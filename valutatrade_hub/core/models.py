"""Core domain models: User, Wallet, Portfolio."""

import hashlib
import os
from datetime import datetime

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)


class User:
    """Represents a registered user in the ValutaTrade Hub system.

    Stores credentials securely using salted SHA-256 hashing.
    Private attributes with getters ensure encapsulation.
    """

    def __init__(
        self,
        username: str,
        password: str = "",
        *,
        salt: str | None = None,
        password_hash: str | None = None,
        created_at: str | None = None,
    ):
        """Initialize a User.

        For new registration pass username and password.
        For loading from DB pass salt, password_hash, and created_at.
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        self.__username: str = username.strip()

        if password_hash and salt:
            self.__salt = salt
            self.__password_hash = password_hash
        else:
            if len(password) < 4:
                raise ValueError("Password must be at least 4 characters")
            self.__salt = os.urandom(16).hex()
            self.__password_hash = self._hash_password(password, self.__salt)

        self.__created_at: str = created_at or datetime.now().isoformat()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash a password with the given salt using SHA-256."""
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Check whether the provided password matches the stored hash."""
        return self.__password_hash == self._hash_password(password, self.__salt)

    @property
    def username(self) -> str:
        """Return the username."""
        return self.__username

    @property
    def created_at(self) -> str:
        """Return the ISO-formatted registration date."""
        return self.__created_at

    def get_user_info(self) -> dict:
        """Return public user info (without password data)."""
        return {
            "username": self.__username,
            "created_at": self.__created_at,
        }

    def to_dict(self) -> dict:
        """Serialize user to a dictionary (for JSON storage)."""
        return {
            "username": self.__username,
            "password_hash": self.__password_hash,
            "salt": self.__salt,
            "created_at": self.__created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Deserialize a User from a dictionary."""
        return cls(
            username=data["username"],
            password="",
            salt=data["salt"],
            password_hash=data["password_hash"],
            created_at=data["created_at"],
        )

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return f"User(username={self.__username!r})"


class Wallet:
    """Represents a single-currency wallet with deposit/withdraw operations.

    Balance is protected via @property with non-negative validation.
    """

    def __init__(self, currency: str, balance: float = 0.0):
        """Initialize a Wallet for the given currency."""
        self.__currency: str = currency.upper()
        self.__balance: float = 0.0
        self.balance = balance  # use the property setter for validation

    @property
    def currency(self) -> str:
        """Return the wallet currency code."""
        return self.__currency

    @property
    def balance(self) -> float:
        """Return the current balance."""
        return self.__balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Set the balance with validation."""
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"Balance must be a number, got {type(value).__name__}"
            )
        if value < 0:
            raise ValueError("Balance cannot be negative")
        self.__balance = float(value)

    def deposit(self, amount: float) -> None:
        """Add funds to the wallet.

        Args:
            amount: Positive number to deposit.

        Raises:
            ValueError: If amount is not a positive number.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Deposit amount must be a positive number")
        self.__balance += amount

    def withdraw(self, amount: float) -> None:
        """Remove funds from the wallet.

        Args:
            amount: Positive number to withdraw.

        Raises:
            ValueError: If amount is not a positive number.
            InsufficientFundsError: If balance is too low.
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Withdrawal amount must be a positive number")
        if amount > self.__balance:
            raise InsufficientFundsError(
                f"Insufficient funds: have {self.__balance:.2f} {self.__currency}, "
                f"need {amount:.2f} {self.__currency}"
            )
        self.__balance -= amount

    def get_balance_info(self) -> str:
        """Return a human-readable balance string."""
        return f"{self.__currency}: {self.__balance:.4f}"

    def to_dict(self) -> dict:
        """Serialize wallet to a dictionary."""
        return {"currency": self.__currency, "balance": self.__balance}

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """Deserialize a Wallet from a dictionary."""
        return cls(currency=data["currency"], balance=data["balance"])

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return f"Wallet({self.__currency}, {self.__balance:.4f})"


class Portfolio:
    """Represents a user's collection of currency wallets.

    Ensures unique currencies and provides portfolio valuation.
    """

    def __init__(self, user: User):
        """Initialize an empty portfolio for the given user."""
        self.__user: User = user
        self.__wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User:
        """Return the portfolio owner (read-only)."""
        return self.__user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Return a shallow copy of the wallets dictionary."""
        return dict(self.__wallets)

    def add_currency(self, currency: str) -> Wallet:
        """Add a new currency wallet or return the existing one.

        Args:
            currency: Currency code (e.g. 'BTC', 'EUR').

        Returns:
            The Wallet for the given currency.
        """
        currency = currency.upper()
        if currency not in self.__wallets:
            self.__wallets[currency] = Wallet(currency)
        return self.__wallets[currency]

    def get_wallet(self, currency: str) -> Wallet:
        """Get an existing wallet by currency code.

        Raises:
            CurrencyNotFoundError: If no wallet exists for the currency.
        """
        currency = currency.upper()
        if currency not in self.__wallets:
            raise CurrencyNotFoundError(
                f"No wallet found for currency '{currency}'"
            )
        return self.__wallets[currency]

    def has_wallet(self, currency: str) -> bool:
        """Check whether a wallet for the given currency exists."""
        return currency.upper() in self.__wallets

    def get_total_value(self, rates: dict, base: str = "USD") -> float:
        """Calculate the total portfolio value in the base currency.

        Args:
            rates: Dict mapping currency codes to their value in USD.
            base: Base currency for valuation (default USD).

        Returns:
            Total value as a float.
        """
        total = 0.0
        base = base.upper()
        base_rate = rates.get(base, 1.0) if base != "USD" else 1.0

        for currency, wallet in self.__wallets.items():
            if wallet.balance == 0:
                continue
            if currency == "USD":
                value_in_usd = wallet.balance
            elif currency in rates:
                value_in_usd = wallet.balance * rates[currency]
            else:
                continue
            total += value_in_usd / base_rate if base_rate else 0.0

        return total

    def to_dict(self) -> dict:
        """Serialize portfolio to a dictionary."""
        return {
            "username": self.__user.username,
            "wallets": {
                code: wallet.to_dict()
                for code, wallet in self.__wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, user: User) -> "Portfolio":
        """Deserialize a Portfolio from a dictionary."""
        portfolio = cls(user)
        for _code, wallet_data in data.get("wallets", {}).items():
            wallet = Wallet.from_dict(wallet_data)
            portfolio.__wallets[wallet.currency] = wallet  # noqa: E501
        return portfolio

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        currencies = ", ".join(self.__wallets.keys())
        return f"Portfolio(user={self.__user.username!r}, wallets=[{currencies}])"
