"""Бизнес-логика: register, login, buy, sell, get-rate, show-portfolio.

Использует:
- currencies.py для валидации валют (get_currency).
- exceptions.py для типизированных ошибок.
- infra/database.py для доступа к данным (DatabaseManager).
- infra/settings.py для конфигурации (SettingsLoader).
- decorators.py для логирования (@log_action).
"""

from datetime import datetime

from valutatrade_hub.core.currencies import (
    CryptoCurrency,
    get_currency,
)
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import (
    Portfolio,
    User,
)
from valutatrade_hub.core.utils import (
    generate_salt,
    get_next_user_id,
    hash_password,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

# ── Регистрация / Вход ───────────────────────────────────


@log_action
def register_user(username: str, password: str) -> str:
    """Зарегистрировать нового пользователя.

    Args:
        username: Имя пользователя.
        password: Пароль (мин. 4 символа).

    Returns:
        Сообщение об успешной регистрации.

    Raises:
        ValueError: Некорректные данные.
    """
    if len(password) < 4:
        raise ValueError(
            "Пароль должен быть не короче 4 символов"
        )

    db = DatabaseManager()
    users = db.load_users()

    for u in users:
        if u["username"].lower() == username.lower():
            raise ValueError(
                f"Имя пользователя '{username}' "
                "уже занято"
            )

    user_id = get_next_user_id(users)
    salt = generate_salt()
    hashed = hash_password(password, salt)

    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed,
        salt=salt,
        registration_date=datetime.now().isoformat(),
    )
    users.append(user.to_dict())
    db.save_users(users)

    portfolio = Portfolio(user_id=user_id)
    db.save_portfolio(portfolio.to_dict())

    return (
        f"Пользователь '{username}' зарегистрирован "
        f"(id={user_id}). "
        f"Войдите: login --username {username} "
        f"--password ****"
    )


@log_action
def login_user(
    username: str, password: str
) -> tuple[User, Portfolio]:
    """Войти в систему.

    Args:
        username: Имя пользователя.
        password: Пароль.

    Returns:
        Кортеж (User, Portfolio).

    Raises:
        ValueError: Неверные учётные данные.
    """
    db = DatabaseManager()
    users = db.load_users()

    user_data = None
    for u in users:
        if u["username"].lower() == username.lower():
            user_data = u
            break

    if not user_data:
        raise ValueError(
            f"Пользователь '{username}' не найден"
        )

    user = User.from_dict(user_data)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    portfolio_data = db.load_portfolio(user.user_id)
    if portfolio_data:
        portfolio = Portfolio.from_dict(portfolio_data)
    else:
        portfolio = Portfolio(user_id=user.user_id)

    return user, portfolio


# ── Портфель ─────────────────────────────────────────────


def show_portfolio(
    user: User,
    portfolio: Portfolio,
    base_currency: str = "USD",
) -> str:
    """Отобразить содержимое портфеля.

    Args:
        user: Объект текущего пользователя.
        portfolio: Объект портфеля.
        base_currency: Базовая валюта для оценки.

    Returns:
        Форматированная строка с портфелем.
    """
    db = DatabaseManager()
    rates = db.load_rates()

    total = _convert_portfolio_value(
        portfolio, rates, base_currency
    )

    lines = [
        f"Портфель пользователя '{user.username}'"
        f" (id={user.user_id})",
        f"Общая оценочная стоимость: "
        f"{total:.2f} {base_currency}",
        "-" * 40,
    ]

    wallets = portfolio.wallets
    if not wallets:
        lines.append("  (пусто)")
    else:
        for code, wallet in sorted(wallets.items()):
            bal = _fmt_balance(
                wallet.balance, code
            )
            val_str = _wallet_value_str(
                wallet.balance,
                code,
                rates,
                base_currency,
            )
            lines.append(
                f"  {code}: {bal}{val_str}"
            )

    return "\n".join(lines)


# ── Покупка / Продажа ────────────────────────────────────


@log_action(verbose=True)
def buy_currency(
    portfolio: Portfolio,
    currency_code: str,
    amount: float,
) -> tuple[Portfolio, str]:
    """Купить валюту.

    Валидирует код через get_currency().
    Автоматически создаёт кошелёк при отсутствии.

    Args:
        portfolio: Портфель текущего пользователя.
        currency_code: Код валюты для покупки.
        amount: Количество (> 0).

    Returns:
        Кортеж (обновлённый Portfolio, сообщение).

    Raises:
        CurrencyNotFoundError: Неизвестная валюта.
        ValueError: Некорректная сумма.
    """
    currency_code = currency_code.upper()
    currency = get_currency(currency_code)

    if amount <= 0:
        raise ValueError(
            "Сумма покупки должна быть положительной"
        )

    wallet = portfolio.get_wallet(currency_code)
    if not wallet:
        wallet = portfolio.add_currency(currency_code)

    wallet.deposit(amount)

    db = DatabaseManager()
    db.save_portfolio(portfolio.to_dict())

    rates = db.load_rates()
    cost_str = _estimate_cost(
        amount, currency_code, rates
    )

    display = currency.get_display_info()
    msg = (
        f"Куплено {_fmt_balance(amount, currency_code)}"
        f" {currency_code}. "
        f"Баланс: "
        f"{_fmt_balance(wallet.balance, currency_code)}"
        f" {currency_code}"
        f"{cost_str}\n"
        f"  {display}"
    )
    return portfolio, msg


@log_action(verbose=True)
def sell_currency(
    portfolio: Portfolio,
    currency_code: str,
    amount: float,
) -> tuple[Portfolio, str]:
    """Продать валюту.

    Проверяет наличие кошелька и достаточность средств.

    Args:
        portfolio: Портфель текущего пользователя.
        currency_code: Код валюты для продажи.
        amount: Количество (> 0).

    Returns:
        Кортеж (обновлённый Portfolio, сообщение).

    Raises:
        CurrencyNotFoundError: Неизвестная валюта.
        InsufficientFundsError: Недостаточно средств.
        ValueError: Некорректная сумма.
    """
    currency_code = currency_code.upper()
    currency = get_currency(currency_code)

    if amount <= 0:
        raise ValueError(
            "Сумма продажи должна быть положительной"
        )

    wallet = portfolio.get_wallet(currency_code)
    if not wallet:
        raise InsufficientFundsError(
            available=0.0,
            required=amount,
            code=currency_code,
        )

    wallet.withdraw(amount)

    db = DatabaseManager()
    db.save_portfolio(portfolio.to_dict())

    rates = db.load_rates()
    revenue_str = _estimate_revenue(
        amount, currency_code, rates
    )

    display = currency.get_display_info()
    msg = (
        f"Продано "
        f"{_fmt_balance(amount, currency_code)}"
        f" {currency_code}. "
        f"Баланс: "
        f"{_fmt_balance(wallet.balance, currency_code)}"
        f" {currency_code}"
        f"{revenue_str}\n"
        f"  {display}"
    )
    return portfolio, msg


# ── Курсы ────────────────────────────────────────────────


def get_rate(
    from_currency: str, to_currency: str
) -> str:
    """Получить курс обмена между валютами.

    Валидирует коды через get_currency().
    Проверяет TTL кеша через SettingsLoader.

    Args:
        from_currency: Код исходной валюты.
        to_currency: Код целевой валюты.

    Returns:
        Строка с информацией о курсе.

    Raises:
        CurrencyNotFoundError: Неизвестная валюта.
        ApiRequestError: Кеш курсов устарел.
    """
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()

    from_curr = get_currency(from_currency)
    to_curr = get_currency(to_currency)

    db = DatabaseManager()
    rates = db.load_rates()

    _check_ttl(rates)

    rate_value = _compute_rate(
        from_currency, to_currency, rates
    )

    if rate_value is None:
        raise ValueError(
            f"Курс {from_currency}/{to_currency} "
            "не найден в данных"
        )

    pair = f"{from_currency}/{to_currency}"
    rate_str = _fmt_rate(rate_value)
    updated = _get_updated_at(
        from_currency, to_currency, rates
    )
    from_info = from_curr.get_display_info()
    to_info = to_curr.get_display_info()

    return (
        f"Курс {pair}: {rate_str}\n"
        f"Обновлено: {updated}\n"
        f"  {from_info}\n"
        f"  {to_info}"
    )


# ── Вспомогательные функции ──────────────────────────────


def _check_ttl(rates: dict) -> None:
    """Проверить актуальность кеша курсов.

    Raises:
        ApiRequestError: Если кеш устарел и обновить
            не удалось.
    """
    settings = SettingsLoader()
    ttl = settings.get("rates_ttl_seconds", 604800)

    last_refresh = rates.get("last_refresh")
    if not last_refresh:
        return

    try:
        refresh_time = datetime.fromisoformat(
            last_refresh
        )
        age = (
            datetime.now() - refresh_time
        ).total_seconds()
        if age > ttl:
            raise ApiRequestError(
                f"Кеш курсов устарел "
                f"({age:.0f}с > TTL {ttl}с). "
                "Обновите курсы или проверьте "
                "Parser Service."
            )
    except ValueError:
        pass


def _compute_rate(
    from_code: str,
    to_code: str,
    rates: dict,
) -> float | None:
    """Вычислить курс обмена.

    Поддерживает прямой, обратный и кросс-курсы
    через USD.
    """
    if from_code == to_code:
        return 1.0

    direct = f"{from_code}_{to_code}"
    if direct in rates and isinstance(
        rates[direct], dict
    ):
        return rates[direct]["rate"]

    reverse = f"{to_code}_{from_code}"
    if reverse in rates and isinstance(
        rates[reverse], dict
    ):
        return 1.0 / rates[reverse]["rate"]

    from_usd = _to_usd(from_code, rates)
    to_usd = _to_usd(to_code, rates)
    if from_usd and to_usd:
        return from_usd / to_usd

    return None


def _to_usd(code: str, rates: dict) -> float | None:
    """Получить курс валюты к USD."""
    if code == "USD":
        return 1.0

    key = f"{code}_USD"
    if key in rates and isinstance(rates[key], dict):
        return rates[key]["rate"]

    key_rev = f"USD_{code}"
    if key_rev in rates and isinstance(
        rates[key_rev], dict
    ):
        return 1.0 / rates[key_rev]["rate"]

    return None


def _get_updated_at(
    from_code: str, to_code: str, rates: dict
) -> str:
    """Извлечь дату обновления из rates."""
    for key in (
        f"{from_code}_{to_code}",
        f"{to_code}_{from_code}",
        f"{from_code}_USD",
        f"USD_{from_code}",
    ):
        info = rates.get(key)
        if isinstance(info, dict) and info.get(
            "updated_at"
        ):
            return info["updated_at"]
    return rates.get("last_refresh", "неизвестно")


def _convert_portfolio_value(
    portfolio: Portfolio,
    rates: dict,
    base: str,
) -> float:
    """Рассчитать стоимость портфеля в base."""
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        if wallet.balance == 0:
            continue
        if code == base:
            total += wallet.balance
        else:
            rate = _compute_rate(code, base, rates)
            if rate:
                total += wallet.balance * rate
    return total


def _wallet_value_str(
    balance: float,
    code: str,
    rates: dict,
    base: str,
) -> str:
    """Строка оценки кошелька в базовой валюте."""
    if balance == 0 or code == base:
        return ""
    rate = _compute_rate(code, base, rates)
    if rate:
        value = balance * rate
        return f" (~{value:.2f} {base})"
    return ""


def _estimate_cost(
    amount: float, code: str, rates: dict
) -> str:
    """Оценочная стоимость покупки в USD."""
    if code == "USD":
        return ""
    rate = _compute_rate(code, "USD", rates)
    if rate:
        cost = amount * rate
        return f"\n  Оценочная стоимость: ~{cost:.2f} USD"
    return ""


def _estimate_revenue(
    amount: float, code: str, rates: dict
) -> str:
    """Оценочная выручка от продажи в USD."""
    if code == "USD":
        return ""
    rate = _compute_rate(code, "USD", rates)
    if rate:
        rev = amount * rate
        return f"\n  Оценочная выручка: ~{rev:.2f} USD"
    return ""


def _fmt_balance(value: float, code: str) -> str:
    """Формат баланса (4 знака для крипто, 2 для фиат)."""
    try:
        curr = get_currency(code)
        if isinstance(curr, CryptoCurrency):
            return f"{value:.4f}"
    except CurrencyNotFoundError:
        if 0 < value < 1:
            return f"{value:.4f}"
    return f"{value:.2f}"


def _fmt_rate(value: float) -> str:
    """Формат курса: 6 знаков после точки."""
    return f"{value:.6f}"
