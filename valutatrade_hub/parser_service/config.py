"""Parser Service configuration: API keys, URLs, currency lists."""

import os

# ── API Keys (from environment variables) ─────────────────

EXCHANGE_RATE_API_KEY: str = os.environ.get("EXCHANGE_RATE_API_KEY", "")

# ── Base URLs ─────────────────────────────────────────────

COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
EXCHANGE_RATE_BASE_URL: str = "https://v6.exchangerate-api.com/v6"

# ── Base currency ─────────────────────────────────────────

BASE_CURRENCY: str = "USD"

# ── Currency lists ────────────────────────────────────────

CRYPTO_CURRENCIES: list[str] = ["BTC", "ETH", "SOL", "DOGE", "XRP"]
FIAT_CURRENCIES: list[str] = ["EUR", "GBP", "JPY", "RUB", "CNY"]

# ── CoinGecko ID mapping ─────────────────────────────────

CRYPTO_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "XRP": "ripple",
}

# ── API settings ──────────────────────────────────────────

API_TIMEOUT: int = 10
