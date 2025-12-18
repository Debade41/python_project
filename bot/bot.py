import logging
from typing import Any, Dict, List

import requests
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def _format_amount(value: float) -> str:
    formatted = f"{value:,.2f}"
    return formatted.replace(",", " ")


def call_worker(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{settings.api_base_url}{endpoint}"
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def greet(update: Update, _: CallbackContext) -> None:
    text = (
        "Привет! Я анализирую текст и конвертирую валюту.\n"
        "Отправьте любое сообщение для анализа" \
        " и получите конвертацию в несколько валют!"
        "Инспользуй /history [число] для просмотра истории конвертации" \
    )
    update.message.reply_text(text)


def analyze(update: Update, context: CallbackContext) -> None:
    text = " ".join(context.args)
    if not text:
        update.message.reply_text("Пришлите текст после команды /analyze")
        return
    _send_analysis(update, text)


def _send_analysis(update: Update, text: str) -> None:
    try:
        data = call_worker("/analyze", {"text": text})
    except requests.RequestException:
        logger.exception("Failed to call analyzer")
        update.message.reply_text("Сервис временно недоступен. Попробуйте позже.")
        return

    reply = (
        "Анализ текста:\n"
        f"Символы: {data['char_count']}\n"
        f"Слова: {data['word_count']}\n"
        f"Тональность: {data['sentiment']} (score {data['sentiment_score']})"
    )
    update.message.reply_text(reply)
    _send_currency_conversions(update, text)


def _send_currency_conversions(update: Update, text: str) -> None:
    try:
        payload = call_worker("/detect-currencies", {"text": text})
    except requests.RequestException:
        logger.exception("Failed to detect currencies")
        return

    items: List[Dict[str, Any]] = payload.get("items") or []
    if not items:
        if update.message.chat.type == "private": 
            update.message.reply_text("В тексте не найдено упоминаний валют")
        return

    lines = ["Конвертация найденных сумм:"]
    for item in items:
        lines.append(f"• {_format_amount(item['source_amount'])} {item['source_currency']}")
        for conversion in item.get("conversions", []):
            lines.append(
                f"    ↳ {_format_amount(conversion['converted_amount'])} {conversion['quote_currency']} "
                f"(курс {conversion['rate']:.4f})"
            )

    update.message.reply_text("\n".join(lines))


def handle_text(update: Update, _: CallbackContext) -> None:
    message = update.message
    if message is None or not message.text:
        return
    text = message.text.strip()
    if text.startswith("/"):
        return
    _send_currency_conversions(update, text)
def history(update: Update, context: CallbackContext) -> None:
    """Показывает историю конвертаций из API"""
    # Получаем количество записей
    args = context.args
    limit = 5
    
    if args:
        try:
            limit = int(args[0])
            limit = max(1, min(limit, 20))
        except ValueError:
            update.message.reply_text(
                "❌ Используйте: /history [число]. Пример: /history 10"
            )
            return
    
    try:
       
        url = f"{settings.api_base_url}/history?limit={limit}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception("Failed to fetch history")
        update.message.reply_text("📛 История временно недоступна.")
        return
    
    conversions = data.get("conversions", [])
    
    if not conversions:
        update.message.reply_text("📭 История конвертаций пуста.")
        return
    
 
    lines = [f"📜 *Последние {len(conversions)} конвертаций:*\n"]
    
    for i, conv in enumerate(conversions, 1):
        time_str = conv.get("created_at", "").replace("T", " ")[11:16]  # ЧЧ:MM
        
        lines.append(
            f"{i}. *{conv['amount']:.2f} {conv['base_currency']}* → "
            f"*{conv['converted_amount']:.2f} {conv['quote_currency']}*\n"
            f"   Курс: {conv['rate']:.4f} | Время: {time_str}\n"
        )
    
    
    lines.append(f"\n🌐 *Полная история:* http://localhost:8501")
    
    update.message.reply_text("\n".join(lines), parse_mode="Markdown")
def convert(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) != 3:
        update.message.reply_text(
            "Используйте формат: /convert <сумма> <из> <в>. Пример: /convert 10 USD RUB"
        )
        return

    amount_text, base, quote = args
    try:
        amount = float(amount_text)
    except ValueError:
        update.message.reply_text("Сумма должна быть числом")
        return

    try:
        data = call_worker(
            "/convert",
            {
                "amount": amount,
                "base_currency": base.upper(),
                "quote_currency": quote.upper(),
            },
        )
    except requests.HTTPError as http_exc:
        if http_exc.response is not None and http_exc.response.status_code == 502:
            detail = http_exc.response.json().get("detail", "Ошибка конвертации")
            update.message.reply_text(detail)
        else:
            update.message.reply_text("Не удалось конвертировать сейчас")
        logger.exception("Conversion failed")
        return
    except requests.RequestException:
        logger.exception("Call to convert endpoint failed")
        update.message.reply_text("Сервис недоступен. Попробуйте позже.")
        return

    reply = (
        f"{data['amount']} {data['base_currency']} = {data['converted_amount']} {data['quote_currency']}\n"
        f"Курс: {data['rate']}"
    )
    update.message.reply_text(reply)


def main() -> None:
    updater = Updater(token=settings.telegram_token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", greet))
    dispatcher.add_handler(CommandHandler("help", greet))
    dispatcher.add_handler(CommandHandler("analyze", analyze))
    dispatcher.add_handler(CommandHandler("convert", convert))
    dispatcher.add_handler(CommandHandler("history", history))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    logger.info("Starting Telegram bot")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
