"""Клиенты внешних API: CoinGecko, ExchangeRate-API.

Абстрактный базовый класс BaseApiClient
с единым методом fetch_rates() -> dict.
"""

import time
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
)
from valutatrade_hub.parser_service.config import (
    ParserConfig,
)


class BaseApiClient(ABC):
    """Абстрактный клиент для получения курсов."""

    def __init__(self, config: ParserConfig):
        """Инициализировать клиент.

        Args:
            config: Конфигурация Parser Service.
        """
        self.config = config

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Имя источника данных."""

    @abstractmethod
    def fetch_rates(self) -> dict:
        """Получить курсы валют.

        Returns:
            Словарь {pair_key: {rate, source, meta}}.

        Raises:
            ApiRequestError: При ошибке запроса.
        """


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для криптовалют.

    Использует CRYPTO_ID_MAP для маппинга
    тикеров (BTC) на CoinGecko ID (bitcoin).
    """

    @property
    def source_name(self) -> str:
        """Имя источника."""
        return "CoinGecko"

    def fetch_rates(self) -> dict:
        """Получить курсы криптовалют.

        Returns:
            {'BTC_USD': {'rate': 59337.21, ...}, ...}
        """
        ids = ",".join(
            self.config.CRYPTO_ID_MAP.values()
        )
        base = self.config.BASE_CURRENCY.lower()
        url = (
            f"{self.config.COINGECKO_URL}"
            f"?ids={ids}&vs_currencies={base}"
        )

        start = time.time()
        try:
            resp = requests.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"CoinGecko: {e}"
            ) from e

        elapsed = int((time.time() - start) * 1000)
        status = resp.status_code

        id_to_code = {
            v: k
            for k, v in self.config.CRYPTO_ID_MAP.items()
        }

        result = {}
        for crypto_id, prices in data.items():
            code = id_to_code.get(crypto_id)
            if code and base in prices:
                key = (
                    f"{code}"
                    f"_{self.config.BASE_CURRENCY}"
                )
                result[key] = {
                    "rate": prices[base],
                    "source": self.source_name,
                    "meta": {
                        "raw_id": crypto_id,
                        "request_ms": elapsed,
                        "status_code": status,
                    },
                }

        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для фиатных валют.

    API-ключ берётся из переменной окружения
    EXCHANGERATE_API_KEY.
    """

    @property
    def source_name(self) -> str:
        """Имя источника."""
        return "ExchangeRate-API"

    def fetch_rates(self) -> dict:
        """Получить курсы фиатных валют.

        Конвертирует ответ API (1 USD = X FIAT)
        в формат X_USD (1 X = Y USD).

        Returns:
            {'EUR_USD': {'rate': 1.0786, ...}, ...}
        """
        key = self.config.EXCHANGERATE_API_KEY
        if not key:
            raise ApiRequestError(
                "ExchangeRate-API: ключ не задан "
                "(EXCHANGERATE_API_KEY)"
            )

        base = self.config.BASE_CURRENCY
        url = (
            f"{self.config.EXCHANGERATE_API_URL}"
            f"/{key}/latest/{base}"
        )

        start = time.time()
        try:
            resp = requests.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"ExchangeRate-API: {e}"
            ) from e

        elapsed = int((time.time() - start) * 1000)
        status = resp.status_code

        if data.get("result") != "success":
            error = data.get(
                "error-type", "unknown error"
            )
            raise ApiRequestError(
                f"ExchangeRate-API: {error}"
            )

        api_rates = data.get(
            "conversion_rates",
            data.get("rates", {}),
        )

        result = {}
        for fiat_code in self.config.FIAT_CURRENCIES:
            raw = api_rates.get(fiat_code)
            if raw and raw > 0:
                pair = f"{fiat_code}_{base}"
                result[pair] = {
                    "rate": 1.0 / raw,
                    "source": self.source_name,
                    "meta": {
                        "raw_rate": raw,
                        "request_ms": elapsed,
                        "status_code": status,
                    },
                }

        return result
