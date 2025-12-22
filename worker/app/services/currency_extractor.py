from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List

CURRENCY_ALIASES = {
    "USD": {"usd", "dollar", "dollars", "доллар", "долларов", "долл", "$", "бакс", "бакса", "баксов", "зеленых"},
    "EUR": {"eur", "euro", "евро", "€", "еврик"},
    "RUB": {"rub", "р", "руб", "руб.", "рублей", "рубля", "₽", "косарь", "деревянный","деревянных"},
    "KZT": {"kzt", "тенге", "тг", "казахстанский тенге"},
    "CNY": {"cny", "yuan", "юань", "юаней", "¥", "元"},
    "CAD": {"cad"},
    "AUD": {"aud"},
    "SGD": {"sgd"},
    "MXN": {"mxn"},
    "SEK": {"sek"},
    "NOK": {"nok"},
}

_alias_tokens = sorted({alias for aliases in CURRENCY_ALIASES.values() for alias in aliases}, key=len, reverse=True)
_alias_group = "|".join(re.escape(token) for token in _alias_tokens)
_suffix_tokens = sorted([
    'миллионов', 'миллиона', 'миллион', 
    'тысяч', 'тысячи', 'тысяча', 
    'млн', 'тыс', 'к', 'k', 'м', 'm'
], key=len, reverse=True)
_suffix_group = "|".join(re.escape(token) for token in _suffix_tokens)
AMOUNT_RE = r"\d[\d\s\u00A0\u202F]*(?:[.,]\d+)?\s*(?:[кk]|тыс|тысяч|[мm]|млн|миллион|миллионов)?"
_CURRENCY_RE = rf"(?:{_alias_group}|[A-Za-z]{{3}}|[$€£¥₽])"

CURRENCY_AFTER = re.compile(rf"(?P<amount>{AMOUNT_RE})\s*(?P<currency>{_CURRENCY_RE})", re.IGNORECASE)
CURRENCY_BEFORE = re.compile(rf"(?P<currency>{_CURRENCY_RE})\s*(?P<amount>{AMOUNT_RE})", re.IGNORECASE)


@dataclass
class CurrencyMention:
    amount: float
    currency: str
    match_text: str
    start: int
    end: int


def _normalize_amount(value: str) -> float | None:
    value_lower=value.lower().strip()
    sanitized = (
        value.replace("\u00A0", "")
        .replace("\u202F", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    
    if sanitized.endswith('.'):
        sanitized = sanitized[:-1]
    suffixes = [
        ('миллионов', 1_000_000),
        ('миллиона', 1_000_000),
        ('миллион', 1_000_000),
        ('тысяч', 1000),
        ('тысячи', 1000),
        ('тысяча', 1000),
        ('млн', 1_000_000),
        ('тыс', 1000),
        ('к', 1000),
        ('k', 1000),
        ('м', 1_000_000),
        ('m', 1_000_000),
    ]
    multiplier = 1
    for suffix, mult in suffixes:
        if sanitized.endswith(suffix):
            multiplier = mult
            sanitized = sanitized[:-len(suffix)]
            break




    sanitized = re.sub(r'[^\d.-]', '', sanitized)
    try:
        return float(sanitized)*multiplier
    except ValueError:
        return None


def _normalize_currency(token: str) -> str | None:
    cleaned = token.strip().lower()
    for code, aliases in CURRENCY_ALIASES.items():
        if cleaned in aliases:
            return code
    if re.fullmatch(r"[a-z]{3}", cleaned):
        return cleaned.upper()
    symbols = {"$": "USD", "€": "EUR", "£": "GBP", "₽": "RUB", "¥": "CNY"}
    return symbols.get(token.strip())


def extract_currency_mentions(text: str) -> List[CurrencyMention]:
    mentions: List[CurrencyMention] = []
    for pattern in (CURRENCY_AFTER, CURRENCY_BEFORE):
        for match in pattern.finditer(text):
            amount_value = _normalize_amount(match.group("amount"))
            currency_code = _normalize_currency(match.group("currency"))
            if amount_value is None or currency_code is None:
                continue
            span = match.span()
            mention = CurrencyMention(
                amount=amount_value,
                currency=currency_code,
                match_text=text[span[0] : span[1]],
                start=span[0],
                end=span[1],
            )
            mentions.append(mention)
    unique: dict[tuple[int, int, str, float], CurrencyMention] = {}
    for item in mentions:
        unique[(item.start, item.end, item.currency, item.amount)] = item
    return list(unique.values())
