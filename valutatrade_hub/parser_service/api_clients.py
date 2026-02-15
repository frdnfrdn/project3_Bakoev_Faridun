"""API clients for fetching exchange rates from external services."""

import logging
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import (
    API_TIMEOUT,
    COINGECKO_BASE_URL,
    CRYPTO_ID_MAP,
    EXCHANGE_RATE_API_KEY,
    EXCHANGE_RATE_BASE_URL,
    FIAT_CURRENCIES,
)

logger = logging.getLogger(__name__)


class BaseApiClient(ABC):
    """Abstract base class for all API clients.

    Subclasses must implement fetch_rates() returning a dict
    of {currency_code: rate_in_usd}.
    """

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Fetch exchange rates from the API.

        Returns:
            Dict mapping currency codes to their value in USD.
            Example: {"BTC": 67000.0, "ETH": 3500.0}
        """


class CoinGeckoClient(BaseApiClient):
    """Fetch cryptocurrency rates from the CoinGecko API.

    Uses the free /simple/price endpoint with CRYPTO_ID_MAP
    to translate internal currency codes to CoinGecko IDs.
    """

    def fetch_rates(self) -> dict[str, float]:
        """Fetch crypto rates from CoinGecko.

        Returns:
            Dict of {symbol: price_in_usd}.

        Raises:
            ApiRequestError: On network or API errors.
        """
        ids = ",".join(CRYPTO_ID_MAP.values())
        url = f"{COINGECKO_BASE_URL}/simple/price"
        params = {"ids": ids, "vs_currencies": "usd"}

        try:
            logger.info("Fetching crypto rates from CoinGecko...")
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            self._check_response(response)
            data = response.json()
        except requests.RequestException as exc:
            raise ApiRequestError(
                f"CoinGecko request failed: {exc}"
            ) from exc

        rates: dict[str, float] = {}
        for symbol, coingecko_id in CRYPTO_ID_MAP.items():
            if coingecko_id in data and "usd" in data[coingecko_id]:
                rates[symbol] = float(data[coingecko_id]["usd"])

        logger.info("CoinGecko returned %d rates", len(rates))
        return rates

    @staticmethod
    def _check_response(response: requests.Response) -> None:
        """Validate the HTTP response status code."""
        if response.status_code == 429:
            raise ApiRequestError("CoinGecko rate limit exceeded (429)")
        if response.status_code == 401:
            raise ApiRequestError("CoinGecko authentication error (401)")
        response.raise_for_status()


class ExchangeRateApiClient(BaseApiClient):
    """Fetch fiat currency rates from ExchangeRate-API.

    Requires an API key set via EXCHANGE_RATE_API_KEY env variable.
    Converts rates so that 1 unit of foreign currency = X USD.
    """

    def fetch_rates(self) -> dict[str, float]:
        """Fetch fiat rates from ExchangeRate-API.

        Returns:
            Dict of {currency_code: value_in_usd}.

        Raises:
            ApiRequestError: If API key is missing or request fails.
        """
        if not EXCHANGE_RATE_API_KEY:
            raise ApiRequestError(
                "EXCHANGE_RATE_API_KEY environment variable is not set. "
                "Register at https://www.exchangerate-api.com/ for a free key."
            )

        url = (
            f"{EXCHANGE_RATE_BASE_URL}/{EXCHANGE_RATE_API_KEY}/latest/USD"
        )

        try:
            logger.info("Fetching fiat rates from ExchangeRate-API...")
            response = requests.get(url, timeout=API_TIMEOUT)
            self._check_response(response)
            data = response.json()
        except requests.RequestException as exc:
            raise ApiRequestError(
                f"ExchangeRate-API request failed: {exc}"
            ) from exc

        if data.get("result") != "success":
            raise ApiRequestError(
                f"ExchangeRate-API error: {data.get('error-type', 'unknown')}"
            )

        conversion_rates = data.get("conversion_rates", {})
        rates: dict[str, float] = {}

        for currency in FIAT_CURRENCIES:
            if currency in conversion_rates:
                api_rate = conversion_rates[currency]
                if api_rate and api_rate > 0:
                    rates[currency] = 1.0 / api_rate

        logger.info("ExchangeRate-API returned %d rates", len(rates))
        return rates

    @staticmethod
    def _check_response(response: requests.Response) -> None:
        """Validate the HTTP response status code."""
        if response.status_code == 429:
            raise ApiRequestError(
                "ExchangeRate-API rate limit exceeded (429)"
            )
        if response.status_code in (401, 403):
            raise ApiRequestError(
                "ExchangeRate-API authentication error — check your API key"
            )
        response.raise_for_status()
