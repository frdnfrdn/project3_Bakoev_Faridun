"""Конфигурация Parser Service.

API-ключи, эндпоинты, списки валют, параметры запросов.
Чувствительные данные (API-ключ) загружаются
из переменных окружения (файл .env).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта
_ENV_PATH = (
    Path(__file__).resolve().parents[2] / ".env"
)
load_dotenv(_ENV_PATH)


@dataclass
class ParserConfig:
    """Настройки для Parser Service.

    Attributes:
        EXCHANGERATE_API_KEY: Ключ API (из env).
        COINGECKO_URL: Эндпоинт CoinGecko.
        EXCHANGERATE_API_URL: Эндпоинт ExchangeRate-API.
        BASE_CURRENCY: Базовая валюта (USD).
        FIAT_CURRENCIES: Фиатные валюты.
        CRYPTO_CURRENCIES: Криптовалюты.
        CRYPTO_ID_MAP: Тикер -> CoinGecko ID.
        REQUEST_TIMEOUT: Таймаут запроса (сек).
    """

    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv(
            "EXCHANGERATE_API_KEY", ""
        )
    )

    COINGECKO_URL: str = (
        "https://api.coingecko.com"
        "/api/v3/simple/price"
    )
    EXCHANGERATE_API_URL: str = (
        "https://v6.exchangerate-api.com/v6"
    )

    BASE_CURRENCY: str = "USD"

    FIAT_CURRENCIES: tuple = (
        "EUR",
        "GBP",
        "RUB",
        "JPY",
        "CNY",
    )
    CRYPTO_CURRENCIES: tuple = (
        "BTC",
        "ETH",
        "SOL",
        "DOGE",
        "XRP",
    )
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "DOGE": "dogecoin",
            "XRP": "ripple",
        }
    )

    REQUEST_TIMEOUT: int = 10
