"""Business logic usecases: register, login, buy, sell, get_rate."""

import logging
from datetime import datetime

from valutatrade_hub.core.exceptions import (
    AuthenticationError,
    CurrencyNotFoundError,
    RatesExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger(__name__)


@log_action
def register_user(
    username: str,
    password: str,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> tuple[User, Portfolio]:
    """Register a new user and create an initial portfolio.

    The user starts with an initial USD balance defined in settings.

    Args:
        username: Desired username.
        password: User password (min 4 characters).
        db: DatabaseManager instance.
        settings: SettingsLoader instance.

    Returns:
        Tuple of (User, Portfolio).

    Raises:
        UserAlreadyExistsError: If username is taken.
        ValueError: If username/password is invalid.
    """
    users_data = db.load_users()
    for u in users_data:
        if u["username"].lower() == username.lower():
            raise UserAlreadyExistsError(
                f"User '{username}' already exists"
            )

    user = User(username, password)
    users_data.append(user.to_dict())
    db.save_users(users_data)

    portfolio = Portfolio(user)
    usd_wallet = portfolio.add_currency(settings.base_currency)
    usd_wallet.deposit(settings.initial_balance)
    db.save_portfolio(username, portfolio.to_dict())

    logger.info(
        "Registered user '%s' with %.2f USD",
        username,
        settings.initial_balance,
    )
    return user, portfolio


@log_action
def login_user(
    username: str,
    password: str,
    db: DatabaseManager,
) -> tuple[User, Portfolio]:
    """Authenticate a user and load their portfolio.

    Args:
        username: Username.
        password: Password to verify.
        db: DatabaseManager instance.

    Returns:
        Tuple of (User, Portfolio).

    Raises:
        UserNotFoundError: If user does not exist.
        AuthenticationError: If password is wrong.
    """
    users_data = db.load_users()
    user_dict = None
    for u in users_data:
        if u["username"].lower() == username.lower():
            user_dict = u
            break

    if user_dict is None:
        raise UserNotFoundError(f"User '{username}' not found")

    user = User.from_dict(user_dict)
    if not user.verify_password(password):
        raise AuthenticationError("Invalid password")

    portfolio_data = db.load_portfolio(username)
    if portfolio_data:
        portfolio = Portfolio.from_dict(portfolio_data, user)
    else:
        portfolio = Portfolio(user)

    logger.info("User '%s' logged in", username)
    return user, portfolio


def _load_and_validate_rates(
    db: DatabaseManager, settings: SettingsLoader
) -> dict[str, float]:
    """Load rates from DB and check TTL.

    Returns:
        Dict of {currency: rate_in_usd}.

    Raises:
        RatesExpiredError: If rates are stale or missing.
    """
    rates_data = db.load_rates()
    rates = rates_data.get("rates", {})
    updated_at = rates_data.get("updated_at")

    if not rates:
        raise RatesExpiredError(
            "No exchange rates available. Run 'update-rates' first."
        )

    if updated_at:
        try:
            updated_time = datetime.fromisoformat(updated_at)
            age_seconds = (datetime.now() - updated_time).total_seconds()
            if age_seconds > settings.rates_ttl:
                logger.warning(
                    "Rates are %.0f seconds old (TTL: %d)",
                    age_seconds,
                    settings.rates_ttl,
                )
                raise RatesExpiredError(
                    f"Exchange rates expired ({age_seconds:.0f}s old, "
                    f"TTL: {settings.rates_ttl}s). "
                    "Run 'update-rates' to refresh."
                )
        except ValueError:
            pass

    return rates


@log_action
def buy_currency(
    portfolio: Portfolio,
    currency: str,
    amount: float,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> str:
    """Buy a specified amount of currency using USD.

    Args:
        portfolio: User's portfolio.
        currency: Currency code to buy (e.g. 'BTC').
        amount: Amount of currency to buy.
        db: DatabaseManager instance.
        settings: SettingsLoader instance.

    Returns:
        Success message string.

    Raises:
        ValueError: If amount is invalid.
        CurrencyNotFoundError: If rate is not available.
        InsufficientFundsError: If USD balance is too low.
        RatesExpiredError: If rates are stale.
    """
    currency = currency.upper()
    if amount <= 0:
        raise ValueError("Amount must be positive")

    rates = _load_and_validate_rates(db, settings)

    if currency not in rates:
        raise CurrencyNotFoundError(
            f"No exchange rate available for '{currency}'"
        )

    rate = rates[currency]
    cost_usd = amount * rate

    usd_wallet = portfolio.add_currency("USD")
    usd_wallet.withdraw(cost_usd)

    target_wallet = portfolio.add_currency(currency)
    target_wallet.deposit(amount)

    db.save_portfolio(portfolio.user.username, portfolio.to_dict())

    return (
        f"Bought {amount:.4f} {currency} for {cost_usd:.2f} USD "
        f"(rate: 1 {currency} = {rate:.4f} USD)"
    )


@log_action
def sell_currency(
    portfolio: Portfolio,
    currency: str,
    amount: float,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> str:
    """Sell a specified amount of currency for USD.

    Args:
        portfolio: User's portfolio.
        currency: Currency code to sell (e.g. 'ETH').
        amount: Amount of currency to sell.
        db: DatabaseManager instance.
        settings: SettingsLoader instance.

    Returns:
        Success message string.

    Raises:
        ValueError: If amount is invalid.
        CurrencyNotFoundError: If rate is not available.
        InsufficientFundsError: If not enough of the currency.
        RatesExpiredError: If rates are stale.
    """
    currency = currency.upper()
    if amount <= 0:
        raise ValueError("Amount must be positive")

    rates = _load_and_validate_rates(db, settings)

    if currency not in rates:
        raise CurrencyNotFoundError(
            f"No exchange rate available for '{currency}'"
        )

    rate = rates[currency]
    revenue_usd = amount * rate

    target_wallet = portfolio.get_wallet(currency)
    target_wallet.withdraw(amount)

    usd_wallet = portfolio.add_currency("USD")
    usd_wallet.deposit(revenue_usd)

    db.save_portfolio(portfolio.user.username, portfolio.to_dict())

    return (
        f"Sold {amount:.4f} {currency} for {revenue_usd:.2f} USD "
        f"(rate: 1 {currency} = {rate:.4f} USD)"
    )


def get_rate(
    currency: str,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> dict:
    """Get the current exchange rate for a currency.

    Args:
        currency: Currency code.
        db: DatabaseManager instance.
        settings: SettingsLoader instance.

    Returns:
        Dict with rate info.

    Raises:
        CurrencyNotFoundError: If rate is not found.
        RatesExpiredError: If rates are stale.
    """
    currency = currency.upper()
    rates = _load_and_validate_rates(db, settings)

    if currency not in rates:
        raise CurrencyNotFoundError(
            f"No exchange rate available for '{currency}'"
        )

    rates_data = db.load_rates()
    return {
        "currency": currency,
        "rate_usd": rates[currency],
        "base": "USD",
        "updated_at": rates_data.get("updated_at", "N/A"),
    }


def get_portfolio_info(
    portfolio: Portfolio,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> dict:
    """Compile portfolio summary with valuations.

    Args:
        portfolio: User's portfolio.
        db: DatabaseManager instance.
        settings: SettingsLoader instance.

    Returns:
        Dict with portfolio info and total value.
    """
    rates_data = db.load_rates()
    rates = rates_data.get("rates", {})

    wallets_info = []
    for currency, wallet in portfolio.wallets.items():
        if currency == "USD":
            value_usd = wallet.balance
        elif currency in rates:
            value_usd = wallet.balance * rates[currency]
        else:
            value_usd = 0.0

        wallets_info.append({
            "currency": currency,
            "balance": wallet.balance,
            "value_usd": value_usd,
        })

    total_value = sum(w["value_usd"] for w in wallets_info)

    return {
        "username": portfolio.user.username,
        "wallets": wallets_info,
        "total_value_usd": total_value,
        "rates_updated_at": rates_data.get("updated_at", "N/A"),
    }
