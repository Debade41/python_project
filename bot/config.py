import os
from dataclasses import dataclass


@dataclass
class Settings:
    telegram_token: str
    api_base_url: str = "http://api:8000"


def get_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    api_base = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
    return Settings(telegram_token=token, api_base_url=api_base)
