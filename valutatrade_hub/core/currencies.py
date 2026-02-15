"""Иерархия валют: базовый класс Currency и наследники.

Реестр валют с фабричным методом get_currency().
"""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты.

    Атрибуты (public):
        code: str — ISO-код или тикер (2-5 символов, верхний регистр).
        name: str — человекочитаемое название.
    """

    def __init__(self, code: str, name: str):
        """Инициализировать валюту с валидацией.

        Args:
            code: Код валюты (2-5 символов, без пробелов).
            name: Название валюты (не пустое).

        Raises:
            ValueError: Если code или name некорректны.
        """
        code = code.strip().upper()
        if not code or len(code) < 2 or len(code) > 5:
            raise ValueError(
                "Код валюты: 2-5 символов верхнего регистра"
            )
        if " " in code:
            raise ValueError(
                "Код валюты не может содержать пробелы"
            )
        if not name or not name.strip():
            raise ValueError(
                "Название валюты не может быть пустым"
            )
        self.code = code
        self.name = name.strip()

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов."""

    def __repr__(self) -> str:
        """Отладочное представление."""
        return f"{type(self).__name__}({self.code!r})"


class FiatCurrency(Currency):
    """Фиатная валюта.

    Доп. атрибут:
        issuing_country: str — страна/зона эмиссии.
    """

    def __init__(
        self, code: str, name: str, issuing_country: str
    ):
        """Инициализировать фиатную валюту.

        Args:
            code: ISO-код (например, USD, EUR).
            name: Название (например, US Dollar).
            issuing_country: Страна эмиссии.
        """
        super().__init__(code, name)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        """Формат: [FIAT] USD — US Dollar (Issuing: US)."""
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта.

    Доп. атрибуты:
        algorithm: str — алгоритм консенсуса.
        market_cap: float — рыночная капитализация.
    """

    def __init__(
        self,
        code: str,
        name: str,
        algorithm: str,
        market_cap: float,
    ):
        """Инициализировать криптовалюту.

        Args:
            code: Тикер (например, BTC, ETH).
            name: Название (например, Bitcoin).
            algorithm: Алгоритм (например, SHA-256).
            market_cap: Капитализация в USD.
        """
        super().__init__(code, name)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        """Формат: [CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, "
            f"MCAP: {self.market_cap:.2e})"
        )


# ── Реестр валют ─────────────────────────────────────────

_CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency(
        "USD", "US Dollar", "United States"
    ),
    "EUR": FiatCurrency("EUR", "Euro", "Eurozone"),
    "GBP": FiatCurrency(
        "GBP", "British Pound", "United Kingdom"
    ),
    "JPY": FiatCurrency("JPY", "Japanese Yen", "Japan"),
    "RUB": FiatCurrency(
        "RUB", "Russian Ruble", "Russia"
    ),
    "CNY": FiatCurrency("CNY", "Chinese Yuan", "China"),
    "BTC": CryptoCurrency(
        "BTC", "Bitcoin", "SHA-256", 1.12e12
    ),
    "ETH": CryptoCurrency(
        "ETH", "Ethereum", "Ethash", 4.2e11
    ),
    "SOL": CryptoCurrency(
        "SOL", "Solana", "Proof of History", 8.5e10
    ),
    "DOGE": CryptoCurrency(
        "DOGE", "Dogecoin", "Scrypt", 2.3e10
    ),
    "XRP": CryptoCurrency(
        "XRP", "Ripple", "RPCA", 3.1e10
    ),
}


def get_currency(code: str) -> Currency:
    """Получить валюту по коду из реестра.

    Args:
        code: Код валюты.

    Returns:
        Объект Currency (Fiat или Crypto).

    Raises:
        CurrencyNotFoundError: Если код не найден.
    """
    code = code.strip().upper()
    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)
    return _CURRENCY_REGISTRY[code]


def get_supported_codes() -> list[str]:
    """Получить список поддерживаемых кодов валют."""
    return sorted(_CURRENCY_REGISTRY.keys())
