from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Currency Text Analyzer API"
    database_url: str
    currency_rates_url: str = "https://www.cbr-xml-daily.ru/daily_json.js"
    request_timeout: int = 10
    currency_cache_ttl: int = 600
    reference_currency: str = "RUB"
    primary_quote_currency: str = "RUB"
    secondary_quote_currency: str | None = "USD"
    additional_quote_currencies: List[str] = ["EUR", "CNY", "KZT"]
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
