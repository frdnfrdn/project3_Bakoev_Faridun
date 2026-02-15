"""RatesUpdater: aggregate exchange rates from multiple API sources."""

import json
import logging
import os
from datetime import datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import BASE_CURRENCY
from valutatrade_hub.parser_service.storage import atomic_write_json

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Fetches rates from all configured API sources and merges them.

    Fault-tolerant: if one client fails, others still proceed.
    Writes to rates.json (current) and appends to exchange_rates.json (history).
    """

    def __init__(self, settings: SettingsLoader | None = None) -> None:
        """Initialize with API clients and settings."""
        self._settings = settings or SettingsLoader()
        self._clients = [
            ("CoinGecko", CoinGeckoClient()),
            ("ExchangeRate-API", ExchangeRateApiClient()),
        ]

    def run_update(self) -> dict[str, float]:
        """Poll all sources, merge, write, and return the combined rates.

        Returns:
            Dict of merged rates {currency: rate_in_usd}.
        """
        merged_rates: dict[str, float] = {}
        errors: list[str] = []

        for name, client in self._clients:
            try:
                rates = client.fetch_rates()
                merged_rates.update(rates)
                logger.info(
                    "Successfully fetched %d rates from %s", len(rates), name
                )
            except ApiRequestError as exc:
                errors.append(f"{name}: {exc}")
                logger.warning("Failed to fetch from %s: %s", name, exc)

        if not merged_rates:
            msg = "All API sources failed:\n" + "\n".join(errors)
            logger.error(msg)
            raise ApiRequestError(msg)

        now = datetime.now().isoformat()

        rates_data = {
            "base": BASE_CURRENCY,
            "rates": merged_rates,
            "updated_at": now,
            "last_refresh": now,
        }
        atomic_write_json(self._settings.rates_path, rates_data)
        logger.info("Saved %d rates to %s", len(merged_rates), "rates.json")

        history_entry = {
            "base": BASE_CURRENCY,
            "rates": dict(merged_rates),
            "updated_at": now,
            "source": "combined",
        }
        self._append_history(history_entry)

        if errors:
            logger.warning(
                "Partial update — some sources failed: %s",
                "; ".join(errors),
            )

        return merged_rates

    def _append_history(self, entry: dict) -> None:
        """Append a rate snapshot to the exchange_rates.json history."""
        path = self._settings.exchange_rates_path

        history: list[dict] = []
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    history = json.load(fh)
                if not isinstance(history, list):
                    history = []
            except (json.JSONDecodeError, OSError):
                history = []

        history.append(entry)
        atomic_write_json(path, history)
        logger.info("Appended snapshot to exchange_rates.json history")
