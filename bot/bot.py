import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

import requests
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
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


MAIN_MENU_BUTTONS = [
    ["💱 Конвертация"],
    ["🕘 История", "📖 FAQ"],
    ["📈 Курсы", "🆘 Техподдержка"],
]

POPULAR_PAIRS = [("USD", "RUB"), ("EUR", "RUB")]


def _main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(MAIN_MENU_BUTTONS, resize_keyboard=True)


def call_worker(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{settings.api_base_url}{endpoint}"
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def greet(update: Update, _: CallbackContext) -> None:
    text = (
        "Привет! Я конвертирую валюту.\n"
        "Отправьте любое сообщение и бот найдёт суммы и сконвертирует их.\n"
        "Используйте /convert <сумма> <из> <в> для явной конвертации или /history <число> для просмотра истории."
    )
    update.message.reply_text(text, reply_markup=_main_menu_keyboard())


def _respond_with_menu_text(update: Update, text: str) -> None:
    update.effective_message.reply_text(text, reply_markup=_main_menu_keyboard())


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
    if text in {"💱 Конвертация", "🕘 История", "📖 FAQ", "📈 Курсы", "🆘 Техподдержка"}:
        if text == "💱 Конвертация":
            _respond_with_menu_text(
                update, "Команда /convert <сумма> <из> <в> рассчитает конвертацию, например /convert 10 USD RUB."
            )
        elif text == "🕘 История":
            _respond_with_menu_text(update, "Команда /history [число] вернёт последние операции. Пример: /history 10.")
        elif text == "📖 FAQ":
            _respond_with_menu_text(
                update,
                "Частые вопросы:\n"
                "• /convert <сумма> <из> <в> — ручная конвертация.\n"
                "• /history [число] — история операций.",
            )
        elif text == "📈 Курсы":
            _send_rates(update)
        elif text == "🆘 Техподдержка":
            _respond_with_menu_text(
                update,
                "Напишите нам: https://t.me/warblow51",
            )
        return
    _send_currency_conversions(update, text)


def history(update: Update, context: CallbackContext) -> None:
    """Показывает историю конвертаций из API"""
    
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
        time_str = _format_moscow_time(conv.get("created_at", ""))
        
        lines.append(
            f"{i}. *{conv['amount']:.2f} {conv['base_currency']}* → "
            f"*{conv['converted_amount']:.2f} {conv['quote_currency']}*\n"
            f"   Курс: {conv['rate']:.4f} | Дата: {time_str}\n"
        )
    
    
    lines.append(f"\n🌐 *Полная история:* http://localhost:8501")
    
    update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _format_moscow_time(value: str) -> str:
    if not value:
        return "—"
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return value.replace("T", " ")[11:16]
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")


def _send_rates(update: Update) -> None:
    lines = ["Актуальные курсы:"]
    for base, quote in POPULAR_PAIRS:
        try:
            data = call_worker(
                "/convert",
                {
                    "amount": 1,
                    "base_currency": base,
                    "quote_currency": quote,
                },
            )
        except requests.RequestException:
            logger.exception("Failed to fetch rates")
            update.message.reply_text("Не получается получить курсы. Попробуйте позже.", reply_markup=_main_menu_keyboard())
            return
        lines.append(f"1 {base} = {data['converted_amount']:.4f} {quote} (курс {data['rate']:.4f})")
    _respond_with_menu_text(update, "\n".join(lines))
def convert(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) != 3:
        update.message.reply_text(
            "🔄 *Используйте:* `/convert <сумма> <из> <в>`\n\n"
            "📝 *Примеры:*\n"
            "• `/convert 100 USD RUB`\n"
            "• `/convert 1.5к EUR USD` (1.5к = 1500)\n"
            "• `/convert 2.5м RUB USD` (2.5м = 2,500,000)\n"
            "• `/convert 5000 ¥ EUR`\n\n"
            "💡 *Поддерживаются:* к=×1000, м=×1,000,000",
            parse_mode="Markdown"
        )
        return
    
    amount_text, base, quote = args
    
    try:
        
        amount = _parse_amount_with_suffix(amount_text)
    except ValueError as e:
        update.message.reply_text(f"❌ Ошибка в сумме: {str(e)}")
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
            update.message.reply_text("❌ Не удалось конвертировать. Проверьте коды валют.")
        logger.exception("Conversion failed")
        return
    except requests.RequestException:
        logger.exception("Call to convert endpoint failed")
        update.message.reply_text("⚠️ Сервис недоступен. Попробуйте позже.")
        return
    
    def format_large_number(num):
        if num >= 1_000_000:
            return f"{num:,.0f}".replace(",", " ")
        elif num >= 10_000:
            return f"{num:,.0f}".replace(",", " ")
        else:
            return f"{num:,.2f}".replace(",", " ")
    
    reply = (
        f"💱 *Конвертация:*\n\n"
        f"*{format_large_number(data['amount'])} {data['base_currency']}* =\n"
        f"*{format_large_number(data['converted_amount'])} {data['quote_currency']}*\n\n"
        f"📊 Курс: 1 {data['base_currency']} = {data['rate']:.6f} {data['quote_currency']}"
    )
    
    update.message.reply_text(reply, parse_mode="Markdown")
def _parse_amount_with_suffix(amount_text: str) -> float:
    """Преобразует строку с 'к' или 'м' в число"""
    amount_text = amount_text.strip().lower()
    
    multiplier = 1
    if amount_text.endswith('к') or amount_text.endswith('k'):
        multiplier = 1000
        amount_text = amount_text[:-1]
    elif amount_text.endswith('тыс'):
        multiplier = 1000
        amount_text = amount_text[:-3]
    elif amount_text.endswith('м') or amount_text.endswith('m'):
        multiplier = 1_000_000
        amount_text = amount_text[:-1]
    elif amount_text.endswith('млн'):
        multiplier = 1_000_000
        amount_text = amount_text[:-3]
    
   
    amount_text = amount_text.replace(',', '.')
    
   
    amount_text = re.sub(r'[^\d.-]', '', amount_text)
    
    try:
        return float(amount_text) * multiplier
    except ValueError:
        raise ValueError(f"Не удалось распознать число: {amount_text}")

def main() -> None:
    updater = Updater(token=settings.telegram_token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", greet))
    dispatcher.add_handler(CommandHandler("help", greet))
    dispatcher.add_handler(CommandHandler("convert", convert))
    dispatcher.add_handler(CommandHandler("history", history))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    logger.info("Starting Telegram bot")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
