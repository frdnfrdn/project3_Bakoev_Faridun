"""Бизнес-логика: регистрация, авторизация, покупка/продажа, курсы."""

from datetime import datetime

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    format_datetime,
    generate_salt,
    get_next_user_id,
    hash_password,
    load_json,
    save_json,
)

# Криптовалюты отображаются с 4 знаками после запятой
_CRYPTO = {"BTC", "ETH", "SOL", "DOGE", "XRP", "LTC"}


def register_user(username: str, password: str) -> str:
    """Зарегистрировать нового пользователя.

    1. Проверить уникальность username.
    2. Сгенерировать user_id (автоинкремент).
    3. Захешировать пароль (SHA-256 + соль).
    4. Сохранить в users.json.
    5. Создать пустой портфель в portfolios.json.

    Args:
        username: Имя пользователя (непустое, уникальное).
        password: Пароль (>= 4 символов).

    Returns:
        Сообщение об успехе.

    Raises:
        ValueError: Имя занято или пароль короткий.
    """
    if len(password) < 4:
        raise ValueError(
            "Пароль должен быть не короче 4 символов"
        )

    users = load_json(USERS_FILE) or []
    for u in users:
        if u["username"].lower() == username.lower():
            raise ValueError(
                f"Имя пользователя '{username}' уже занято"
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
    save_json(USERS_FILE, users)

    portfolios = load_json(PORTFOLIOS_FILE) or []
    portfolio = Portfolio(user_id=user_id)
    portfolios.append(portfolio.to_dict())
    save_json(PORTFOLIOS_FILE, portfolios)

    return (
        f"Пользователь '{username}' зарегистрирован "
        f"(id={user_id}). "
        f"Войдите: login --username {username} "
        f"--password ****"
    )


def login_user(
    username: str, password: str
) -> tuple[User, Portfolio]:
    """Войти в систему.

    1. Найти пользователя по username.
    2. Сравнить хеш пароля.

    Args:
        username: Имя пользователя.
        password: Пароль.

    Returns:
        Кортеж (User, Portfolio).

    Raises:
        ValueError: Пользователь не найден или неверный пароль.
    """
    users = load_json(USERS_FILE) or []
    user_dict = None
    for u in users:
        if u["username"].lower() == username.lower():
            user_dict = u
            break

    if user_dict is None:
        raise ValueError(
            f"Пользователь '{username}' не найден"
        )

    user = User.from_dict(user_dict)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    portfolio = _load_portfolio(user.user_id)
    return user, portfolio


def show_portfolio(
    user: User,
    portfolio: Portfolio,
    base_currency: str = "USD",
) -> str:
    """Показать портфель с оценкой в базовой валюте.

    Args:
        user: Текущий пользователь.
        portfolio: Портфель пользователя.
        base_currency: Валюта для оценки (по умолч. USD).

    Returns:
        Отформатированная строка.

    Raises:
        ValueError: Неизвестная базовая валюта.
    """
    rates = _load_rates()

    if base_currency != "USD":
        key = f"{base_currency}_USD"
        info = rates.get(key)
        if not info or not isinstance(info, dict):
            raise ValueError(
                f"Неизвестная базовая валюта "
                f"'{base_currency}'"
            )

    wallets = portfolio.wallets
    if not wallets:
        return (
            f"Портфель пользователя "
            f"'{user.username}' пуст."
        )

    name = user.username
    lines = [
        f"Портфель пользователя '{name}' "
        f"(база: {base_currency}):"
    ]

    total = 0.0
    for code, wallet in wallets.items():
        value = _convert_to_base(
            code, wallet.balance, base_currency, rates
        )
        total += value
        bal = _fmt_balance(wallet.balance, code)
        lines.append(
            f"  - {code}: {bal}  "
            f"-> {value:.2f} {base_currency}"
        )

    lines.append("  " + "-" * 33)
    lines.append(f"  ИТОГО: {total:,.2f} {base_currency}")
    return "\n".join(lines)


def buy_currency(
    portfolio: Portfolio,
    currency_code: str,
    amount: float,
) -> tuple[Portfolio, str]:
    """Купить валюту (добавить в портфель).

    1. Валидировать currency и amount > 0.
    2. Автосоздание кошелька при необходимости.
    3. Увеличить баланс на amount.
    4. Показать оценочную стоимость покупки.

    Args:
        portfolio: Портфель пользователя.
        currency_code: Код покупаемой валюты.
        amount: Количество.

    Returns:
        Кортеж (обновлённый Portfolio, сообщение).

    Raises:
        ValueError: Некорректная сумма.
    """
    currency_code = currency_code.upper()
    if amount <= 0:
        raise ValueError(
            "'amount' должен быть положительным числом"
        )

    rates = _load_rates()
    rate_key = f"{currency_code}_USD"
    rate_info = rates.get(rate_key)

    wallet = portfolio.get_wallet(currency_code)
    old_bal = wallet.balance if wallet else 0.0

    if not wallet:
        wallet = portfolio.add_currency(currency_code)

    wallet.deposit(amount)
    new_bal = wallet.balance
    _save_portfolio(portfolio)

    old_s = _fmt_balance(old_bal, currency_code)
    new_s = _fmt_balance(new_bal, currency_code)
    amt_s = _fmt_balance(amount, currency_code)

    lines = []
    if rate_info and isinstance(rate_info, dict):
        rate = rate_info["rate"]
        cost = amount * rate
        lines.append(
            f"Покупка выполнена: {amt_s} {currency_code} "
            f"по курсу {rate:.2f} USD/{currency_code}"
        )
        lines.append("Изменения в портфеле:")
        lines.append(
            f"  - {currency_code}: "
            f"было {old_s} -> стало {new_s}"
        )
        lines.append(
            f"Оценочная стоимость покупки: "
            f"{cost:,.2f} USD"
        )
    else:
        lines.append(
            f"Покупка выполнена: {amt_s} {currency_code}"
        )
        lines.append("Изменения в портфеле:")
        lines.append(
            f"  - {currency_code}: "
            f"было {old_s} -> стало {new_s}"
        )
        lines.append(
            f"Не удалось получить курс для "
            f"{currency_code}->USD"
        )

    return portfolio, "\n".join(lines)


def sell_currency(
    portfolio: Portfolio,
    currency_code: str,
    amount: float,
) -> tuple[Portfolio, str]:
    """Продать валюту (убрать из портфеля).

    1. Валидировать currency и amount > 0.
    2. Проверить наличие кошелька и достаточность средств.
    3. Уменьшить баланс.
    4. Показать оценочную выручку.

    Args:
        portfolio: Портфель пользователя.
        currency_code: Код продаваемой валюты.
        amount: Количество.

    Returns:
        Кортеж (обновлённый Portfolio, сообщение).

    Raises:
        ValueError: Нет кошелька, недостаточно средств,
                    или некорректная сумма.
    """
    currency_code = currency_code.upper()
    if amount <= 0:
        raise ValueError(
            "'amount' должен быть положительным числом"
        )

    wallet = portfolio.get_wallet(currency_code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{currency_code}'. "
            "Добавьте валюту: она создаётся "
            "автоматически при первой покупке."
        )

    old_bal = wallet.balance
    wallet.withdraw(amount)
    new_bal = wallet.balance
    _save_portfolio(portfolio)

    rates = _load_rates()
    rate_key = f"{currency_code}_USD"
    rate_info = rates.get(rate_key)

    old_s = _fmt_balance(old_bal, currency_code)
    new_s = _fmt_balance(new_bal, currency_code)
    amt_s = _fmt_balance(amount, currency_code)

    lines = []
    if rate_info and isinstance(rate_info, dict):
        rate = rate_info["rate"]
        revenue = amount * rate
        lines.append(
            f"Продажа выполнена: "
            f"{amt_s} {currency_code} "
            f"по курсу {rate:.2f} USD/{currency_code}"
        )
        lines.append("Изменения в портфеле:")
        lines.append(
            f"  - {currency_code}: "
            f"было {old_s} -> стало {new_s}"
        )
        lines.append(
            f"Оценочная выручка: {revenue:,.2f} USD"
        )
    else:
        lines.append(
            f"Продажа выполнена: "
            f"{amt_s} {currency_code}"
        )
        lines.append("Изменения в портфеле:")
        lines.append(
            f"  - {currency_code}: "
            f"было {old_s} -> стало {new_s}"
        )

    return portfolio, "\n".join(lines)


def get_rate(from_currency: str, to_currency: str) -> str:
    """Получить курс валюты.

    Ищет курс в rates.json, при необходимости
    конвертирует через USD.

    Args:
        from_currency: Исходная валюта.
        to_currency: Целевая валюта.

    Returns:
        Отформатированная строка с курсом.

    Raises:
        ValueError: Курс недоступен.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if not from_currency or not to_currency:
        raise ValueError(
            "Коды валют не могут быть пустыми"
        )

    rates = _load_rates()
    result = _compute_rate(
        from_currency, to_currency, rates
    )

    if result is None:
        raise ValueError(
            f"Курс {from_currency}->{to_currency} "
            "недоступен. Повторите попытку позже."
        )

    rate_val, reverse_val, updated_at = result
    ts = format_datetime(updated_at)

    lines = [
        f"Курс {from_currency}->{to_currency}: "
        f"{_fmt_rate(rate_val)} "
        f"(обновлено: {ts})",
    ]
    if reverse_val is not None:
        lines.append(
            f"Обратный курс "
            f"{to_currency}->{from_currency}: "
            f"{_fmt_rate(reverse_val)}"
        )
    return "\n".join(lines)


# ── Вспомогательные функции ──────────────────────────────


def _load_rates() -> dict:
    """Загрузить курсы из rates.json."""
    data = load_json(RATES_FILE)
    return data if isinstance(data, dict) else {}


def _load_portfolio(user_id: int) -> Portfolio:
    """Загрузить портфель пользователя по ID."""
    portfolios = load_json(PORTFOLIOS_FILE) or []
    for p in portfolios:
        if p.get("user_id") == user_id:
            return Portfolio.from_dict(p)
    return Portfolio(user_id=user_id)


def _save_portfolio(portfolio: Portfolio) -> None:
    """Сохранить портфель в portfolios.json."""
    portfolios = load_json(PORTFOLIOS_FILE) or []
    updated = False
    for i, p in enumerate(portfolios):
        if p.get("user_id") == portfolio.user_id:
            portfolios[i] = portfolio.to_dict()
            updated = True
            break
    if not updated:
        portfolios.append(portfolio.to_dict())
    save_json(PORTFOLIOS_FILE, portfolios)


def _convert_to_base(
    code: str,
    balance: float,
    base: str,
    rates: dict,
) -> float:
    """Конвертировать баланс валюты в базовую."""
    if code == base:
        return balance
    key = f"{code}_{base}"
    info = rates.get(key)
    if info and isinstance(info, dict):
        return balance * info["rate"]
    if base != "USD":
        usd_key = f"{code}_USD"
        base_key = f"{base}_USD"
        usd_info = rates.get(usd_key)
        base_info = rates.get(base_key)
        if (
            usd_info
            and isinstance(usd_info, dict)
            and base_info
            and isinstance(base_info, dict)
            and base_info["rate"] > 0
        ):
            val_usd = balance * usd_info["rate"]
            return val_usd / base_info["rate"]
    return 0.0


def _compute_rate(
    from_c: str, to_c: str, rates: dict
) -> tuple[float, float | None, str | None] | None:
    """Вычислить курс обмена между двумя валютами."""
    if from_c == "USD":
        key = f"{to_c}_USD"
        info = rates.get(key)
        if info and isinstance(info, dict):
            to_usd = info["rate"]
            if to_usd and to_usd > 0:
                rate = 1.0 / to_usd
                upd = info.get("updated_at")
                return rate, to_usd, upd

    elif to_c == "USD":
        key = f"{from_c}_USD"
        info = rates.get(key)
        if info and isinstance(info, dict):
            rate = info["rate"]
            if rate and rate > 0:
                upd = info.get("updated_at")
                return rate, 1.0 / rate, upd

    else:
        f_key = f"{from_c}_USD"
        t_key = f"{to_c}_USD"
        f_info = rates.get(f_key)
        t_info = rates.get(t_key)
        if (
            f_info
            and isinstance(f_info, dict)
            and t_info
            and isinstance(t_info, dict)
        ):
            f_usd = f_info["rate"]
            t_usd = t_info["rate"]
            if f_usd and t_usd and t_usd > 0:
                rate = f_usd / t_usd
                rev = t_usd / f_usd if f_usd > 0 else None
                upd = f_info.get("updated_at")
                return rate, rev, upd

    return None


def _fmt_rate(value: float) -> str:
    """Форматировать значение курса."""
    if abs(value) >= 1:
        return f"{value:.2f}"
    return f"{value:.8f}"


def _fmt_balance(value: float, currency: str) -> str:
    """Форматировать баланс валюты."""
    if currency.upper() in _CRYPTO:
        return f"{value:.4f}"
    return f"{value:.2f}"
