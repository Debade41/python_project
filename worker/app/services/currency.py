from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import requests

from ..config import get_settings

settings = get_settings()


class CurrencyServiceError(Exception):
    pass


_reference_rates_cache: tuple[float, Dict[str, float]] | None = None


def _get_reference_rates() -> Dict[str, float]:
    global _reference_rates_cache
    now = time.time()
    cached = _reference_rates_cache
    if cached and now - cached[0] <= settings.currency_cache_ttl:
        return cached[1]

    try:
        response = requests.get(settings.currency_rates_url, timeout=settings.request_timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CurrencyServiceError("failed to fetch conversion rates") from exc

    payload = response.json()
    rates = _parse_rates(payload)

    _reference_rates_cache = (now, rates)
    return rates


def _parse_rates(payload: Dict[str, Any]) -> Dict[str, float]:
    base = settings.reference_currency.upper()

    if "rates" in payload:
        rates = {code.upper(): float(value) for code, value in payload["rates"].items()}
    elif "conversion_rates" in payload:
        rates = {code.upper(): float(value) for code, value in payload["conversion_rates"].items()}
    elif "Valute" in payload:
        rates_rub: Dict[str, float] = {"RUB": 1.0}
        for code, info in payload["Valute"].items():
            try:
                nominal = float(info.get("Nominal", 1)) or 1.0
                value = float(info["Value"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CurrencyServiceError("invalid data from currency provider") from exc
            rub_per_unit = value / nominal
            rates_rub[code.upper()] = 1.0 / rub_per_unit
        if base not in rates_rub:
            raise CurrencyServiceError("reference currency not available in rates")
        base_rate = rates_rub[base]
        rates = {code: val / base_rate for code, val in rates_rub.items()}
    else:
        raise CurrencyServiceError("failed to fetch conversion rates")

    if base not in rates:
        raise CurrencyServiceError("reference currency not available in rates")
    return rates


def convert_currency(amount: float, base: str, quote: str) -> Tuple[float, float]:
    base = base.upper()
    quote = quote.upper()

    if base == quote:
        return 1.0, amount

    rates = _get_reference_rates()

    def _rate_for(currency: str) -> float:
        if currency == settings.reference_currency.upper():
            return 1.0
        value = rates.get(currency)
        if value is None:
            raise CurrencyServiceError("currency pair is not supported")
        return float(value)

    try:
        base_rate = _rate_for(base)
        quote_rate = _rate_for(quote)
    except CurrencyServiceError:
        raise

    rate = quote_rate / base_rate

    converted = round(amount * float(rate), 4)
    return float(rate), converted
