"""Декораторы: @log_action для логирования операций.

Применяется к buy/sell (и опционально register/login)
в usecases.py. Не глотает исключения — пробрасывает,
но фиксирует в лог.
"""

import functools
import inspect
import logging

_logger = logging.getLogger("valutatrade_hub.actions")

_ACTION_MAP = {
    "register_user": "REGISTER",
    "login_user": "LOGIN",
    "buy_currency": "BUY",
    "sell_currency": "SELL",
}


def log_action(func=None, *, verbose=False):
    """Декоратор логирования доменных операций.

    Логирует на уровне INFO: action, user, currency,
    amount, result. При ошибке — ERROR с типом и текстом.

    При verbose=True добавляет контекст (состояние
    кошелька «было -> стало»).

    Использование::

        @log_action
        def buy_currency(...): ...

        @log_action(verbose=True)
        def sell_currency(...): ...
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            params = _bind_params(fn, args, kwargs)
            action = _ACTION_MAP.get(
                fn.__name__, fn.__name__.upper()
            )
            user = _extract_user(params)
            currency = params.get("currency_code", "")
            amount = params.get("amount", "")

            before = ""
            if verbose and currency:
                before = _wallet_state(params, currency)

            try:
                result = fn(*args, **kwargs)
                parts = _build_parts(
                    action, user, currency, amount
                )
                parts.append("result=OK")
                if verbose and before:
                    after = _wallet_state(params, currency)
                    parts.append(
                        f"before={before} after={after}"
                    )
                _logger.info(" ".join(parts))
                return result
            except Exception as exc:
                parts = _build_parts(
                    action, user, currency, amount
                )
                parts.append("result=ERROR")
                parts.append(
                    f"error_type={type(exc).__name__}"
                )
                parts.append(f"error_message='{exc}'")
                _logger.error(" ".join(parts))
                raise

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def _bind_params(fn, args, kwargs) -> dict:
    """Связать аргументы вызова с именами параметров."""
    try:
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except (ValueError, TypeError):
        return {}


def _build_parts(
    action: str,
    user: str,
    currency: str,
    amount,
) -> list[str]:
    """Собрать базовые части лог-сообщения."""
    parts = [action, f"user='{user}'"]
    if currency:
        parts.append(f"currency='{currency}'")
    if amount:
        parts.append(f"amount={amount}")
    return parts


def _extract_user(params: dict) -> str:
    """Извлечь имя/id пользователя из параметров."""
    if "portfolio" in params:
        p = params["portfolio"]
        if hasattr(p, "user_id"):
            return str(p.user_id)
    if "username" in params:
        return str(params["username"])
    if "user" in params:
        u = params["user"]
        if hasattr(u, "username"):
            return u.username
    return "unknown"


def _wallet_state(params: dict, currency: str) -> str:
    """Получить текущий баланс кошелька."""
    portfolio = params.get("portfolio")
    if portfolio and hasattr(portfolio, "get_wallet"):
        wallet = portfolio.get_wallet(currency)
        if wallet:
            return f"{wallet.balance:.4f}"
    return "N/A"
