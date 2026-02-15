"""Модели данных: User, Wallet, Portfolio."""

from datetime import datetime

from valutatrade_hub.core.exceptions import (
    InsufficientFundsError,
)
from valutatrade_hub.core.utils import (
    generate_salt,
    hash_password,
)


class User:
    """Пользователь системы ValutaTrade Hub.

    Хранит данные аутентификации с хешированием (SHA-256 + соль).
    Все атрибуты приватные с геттерами/сеттерами.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: str | None = None,
    ):
        """Инициализировать пользователя.

        Args:
            user_id: Уникальный идентификатор.
            username: Имя пользователя.
            hashed_password: Хеш пароля.
            salt: Соль для хеширования.
            registration_date: Дата регистрации (ISO).
        """
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = (
            registration_date or datetime.now().isoformat()
        )

    # ── Свойства ──────────────────────────────────────

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Установить имя с проверкой на пустоту."""
        if not value or not value.strip():
            raise ValueError(
                "Имя пользователя не может быть пустым"
            )
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Хеш пароля (только чтение)."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль для хеширования (только чтение)."""
        return self._salt

    @property
    def registration_date(self) -> str:
        """Дата регистрации в формате ISO."""
        return self._registration_date

    # ── Методы ────────────────────────────────────────

    def get_user_info(self) -> dict:
        """Информация о пользователе (без пароля).

        Returns:
            Словарь с user_id, username, registration_date.
        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date,
        }

    def change_password(self, new_password: str) -> None:
        """Изменить пароль пользователя.

        Args:
            new_password: Новый пароль (мин. 4 символа).

        Raises:
            ValueError: Если пароль слишком короткий.
        """
        if len(new_password) < 4:
            raise ValueError(
                "Пароль должен быть не короче 4 символов"
            )
        self._salt = generate_salt()
        self._hashed_password = hash_password(
            new_password, self._salt
        )

    def verify_password(self, password: str) -> bool:
        """Проверить введённый пароль на совпадение."""
        return self._hashed_password == hash_password(
            password, self._salt
        )

    # ── Сериализация ──────────────────────────────────

    def to_dict(self) -> dict:
        """Сериализовать пользователя в словарь."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Создать пользователя из словаря."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=data.get(
                "registration_date"
            ),
        )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return (
            f"User(id={self._user_id}, "
            f"username={self._username!r})"
        )


class Wallet:
    """Кошелёк для одной конкретной валюты.

    Баланс защищён через @property с проверкой
    на отрицательные значения и некорректные типы.
    При недостатке средств — InsufficientFundsError.
    """

    def __init__(
        self, currency_code: str, balance: float = 0.0
    ):
        """Инициализировать кошелёк.

        Args:
            currency_code: Код валюты.
            balance: Начальный баланс (по умолч. 0.0).
        """
        self.currency_code = currency_code.upper()
        self._balance: float = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Установить баланс с валидацией."""
        if not isinstance(value, (int, float)):
            raise ValueError(
                "Баланс должен быть числом, "
                f"получен {type(value).__name__}"
            )
        if value < 0:
            raise ValueError(
                "Баланс не может быть отрицательным"
            )
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнить баланс.

        Args:
            amount: Сумма пополнения (> 0).

        Raises:
            ValueError: Если amount не положительное число.
        """
        if (
            not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError(
                "Сумма пополнения должна быть "
                "положительным числом"
            )
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """Снять средства с кошелька.

        Args:
            amount: Сумма снятия (> 0).

        Raises:
            ValueError: Если amount некорректен.
            InsufficientFundsError: Недостаточно средств.
        """
        if (
            not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError(
                "Сумма снятия должна быть "
                "положительным числом"
            )
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self.currency_code,
            )
        self._balance -= amount

    def get_balance_info(self) -> str:
        """Информация о текущем балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"

    # ── Сериализация ──────────────────────────────────

    def to_dict(self) -> dict:
        """Сериализовать кошелёк в словарь."""
        return {"balance": self._balance}

    @classmethod
    def from_dict(
        cls, currency_code: str, data: dict
    ) -> "Wallet":
        """Создать кошелёк из словаря."""
        return cls(
            currency_code=currency_code,
            balance=data.get("balance", 0.0),
        )

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return (
            f"Wallet({self.currency_code}, "
            f"{self._balance:.4f})"
        )


class Portfolio:
    """Портфель — все кошельки одного пользователя.

    Обеспечивает уникальность валют и расчёт стоимости.
    """

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
    ):
        """Инициализировать портфель.

        Args:
            user_id: ID пользователя-владельца.
            wallets: Словарь кошельков (опционально).
        """
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets or {}

    @property
    def user_id(self) -> int:
        """ID пользователя (только чтение)."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков."""
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавить новый кошелёк (если его ещё нет).

        Args:
            currency_code: Код валюты.

        Returns:
            Объект Wallet для данной валюты.
        """
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            return self._wallets[currency_code]
        wallet = Wallet(currency_code)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(
        self, currency_code: str
    ) -> Wallet | None:
        """Получить кошелёк по коду валюты."""
        return self._wallets.get(currency_code.upper())

    def get_total_value(
        self,
        rates: dict,
        base_currency: str = "USD",
    ) -> float:
        """Общая стоимость портфеля в базовой валюте."""
        total = 0.0
        for code, wallet in self._wallets.items():
            if wallet.balance == 0:
                continue
            if code == base_currency:
                total += wallet.balance
            else:
                key = f"{code}_{base_currency}"
                info = rates.get(key)
                if info and isinstance(info, dict):
                    total += wallet.balance * info["rate"]
        return total

    # ── Сериализация ──────────────────────────────────

    def to_dict(self) -> dict:
        """Сериализовать портфель в словарь."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: w.to_dict()
                for code, w in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        """Создать портфель из словаря."""
        user_id = data["user_id"]
        wallets = {}
        for code, w_data in data.get(
            "wallets", {}
        ).items():
            wallets[code] = Wallet.from_dict(
                code, w_data
            )
        return cls(user_id=user_id, wallets=wallets)

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        codes = ", ".join(self._wallets.keys())
        return (
            f"Portfolio(user_id={self._user_id}, "
            f"wallets=[{codes}])"
        )
