"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение приложения."""


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств на кошельке.

    Выбрасывается в Wallet.withdraw() и usecases.sell().
    """

    def __init__(
        self,
        available: float,
        required: float,
        code: str,
    ):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: "
            f"доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта.

    Выбрасывается в currencies.get_currency()
    и при валидации входа в get-rate.
    """

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Сбой внешнего API.

    Выбрасывается в слое получения курсов
    (Parser Service / заглушка).
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            "Ошибка при обращении к внешнему API: "
            f"{reason}"
        )
