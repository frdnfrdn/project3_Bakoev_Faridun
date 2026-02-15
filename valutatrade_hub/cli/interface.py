"""Командный интерфейс (CLI) для ValutaTrade Hub.

CLI является единственной точкой входа для пользовательских
команд. Внутри CLI не дублируется бизнес-логика — только
вызовы методов из core/usecases.py.
"""

import shlex
import sys

from valutatrade_hub.core import usecases
from valutatrade_hub.core.models import Portfolio, User

HELP_TEXT = """
Доступные команды:
  register --username <имя> --password <пароль>
  login --username <имя> --password <пароль>
  logout
  show-portfolio [--base <валюта>]
  buy --currency <код> --amount <кол-во>
  sell --currency <код> --amount <кол-во>
  get-rate --from <валюта> --to <валюта>
  help
  exit / quit
""".strip()


def run_cli() -> None:
    """Главный цикл командного интерфейса."""
    current_user: User | None = None
    current_portfolio: Portfolio | None = None

    print("=" * 50)
    print("  ValutaTrade Hub")
    print("  Введите 'help' для списка команд.")
    print("=" * 50)

    while True:
        try:
            prompt = ""
            if current_user:
                prompt = f"[{current_user.username}] "
            raw = input(f"\n{prompt}> ").strip()
            if not raw:
                continue

            cmd, args = _parse_input(raw)
            flags = _parse_flags(args)

            if cmd in ("exit", "quit"):
                print("До свидания!")
                break

            if cmd == "help":
                print(HELP_TEXT)

            elif cmd == "register":
                _handle_register(flags)

            elif cmd == "login":
                result = _handle_login(flags)
                if result:
                    current_user = result[0]
                    current_portfolio = result[1]

            elif cmd == "logout":
                current_user = None
                current_portfolio = None
                print("Вы вышли из аккаунта.")

            elif cmd == "show-portfolio":
                _require_login(current_user)
                _handle_show_portfolio(
                    current_user,
                    current_portfolio,
                    flags,
                )

            elif cmd == "buy":
                _require_login(current_user)
                current_portfolio = _handle_buy(
                    current_portfolio, flags
                )

            elif cmd == "sell":
                _require_login(current_user)
                current_portfolio = _handle_sell(
                    current_portfolio, flags
                )

            elif cmd == "get-rate":
                _handle_get_rate(flags)

            else:
                print(
                    f"Неизвестная команда: '{cmd}'. "
                    "Введите 'help' для справки."
                )

        except KeyboardInterrupt:
            print("\nДо свидания!")
            break
        except EOFError:
            print("\nДо свидания!")
            break
        except ValueError as exc:
            print(f"Ошибка: {exc}")


# ── Парсинг ввода ────────────────────────────────────────


def _parse_input(
    raw: str,
) -> tuple[str, list[str]]:
    """Разобрать строку на команду и аргументы.

    Использует shlex для безопасного разбора строки.
    На Windows отключает POSIX-режим для совместимости.
    """
    posix = sys.platform != "win32"
    parts = shlex.split(raw, posix=posix)
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def _parse_flags(
    args: list[str],
) -> dict[str, str]:
    """Разобрать аргументы вида --key value в словарь.

    Args:
        args: Список токенов после команды.

    Returns:
        Словарь {ключ: значение}.
    """
    flags: dict[str, str] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--") and len(arg) > 2:
            key = arg[2:]
            if (
                i + 1 < len(args)
                and not args[i + 1].startswith("--")
            ):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = ""
                i += 1
        else:
            i += 1
    return flags


def _require_login(user: User | None) -> None:
    """Проверить, что пользователь авторизован.

    Raises:
        ValueError: Если не выполнен login.
    """
    if user is None:
        raise ValueError("Сначала выполните login")


# ── Обработчики команд ───────────────────────────────────


def _handle_register(flags: dict) -> None:
    """Обработать команду register."""
    username = flags.get("username", "").strip()
    password = flags.get("password", "").strip()

    if not username or not password:
        print(
            "Использование: register "
            "--username <имя> --password <пароль>"
        )
        return

    msg = usecases.register_user(username, password)
    print(msg)


def _handle_login(
    flags: dict,
) -> tuple[User, Portfolio] | None:
    """Обработать команду login."""
    username = flags.get("username", "").strip()
    password = flags.get("password", "").strip()

    if not username or not password:
        print(
            "Использование: login "
            "--username <имя> --password <пароль>"
        )
        return None

    user, portfolio = usecases.login_user(
        username, password
    )
    print(f"Вы вошли как '{username}'")
    return user, portfolio


def _handle_show_portfolio(
    user: User,
    portfolio: Portfolio,
    flags: dict,
) -> None:
    """Обработать команду show-portfolio."""
    base = flags.get("base", "USD").upper()
    result = usecases.show_portfolio(
        user, portfolio, base
    )
    print(result)


def _handle_buy(
    portfolio: Portfolio, flags: dict
) -> Portfolio:
    """Обработать команду buy."""
    currency = flags.get("currency", "").strip().upper()
    amount_str = flags.get("amount", "").strip()

    if not currency or not amount_str:
        print(
            "Использование: buy "
            "--currency <код> --amount <кол-во>"
        )
        return portfolio

    try:
        amount = float(amount_str)
    except ValueError:
        raise ValueError(
            f"'{amount_str}' не является числом"
        ) from None

    portfolio, msg = usecases.buy_currency(
        portfolio, currency, amount
    )
    print(msg)
    return portfolio


def _handle_sell(
    portfolio: Portfolio, flags: dict
) -> Portfolio:
    """Обработать команду sell."""
    currency = flags.get("currency", "").strip().upper()
    amount_str = flags.get("amount", "").strip()

    if not currency or not amount_str:
        print(
            "Использование: sell "
            "--currency <код> --amount <кол-во>"
        )
        return portfolio

    try:
        amount = float(amount_str)
    except ValueError:
        raise ValueError(
            f"'{amount_str}' не является числом"
        ) from None

    portfolio, msg = usecases.sell_currency(
        portfolio, currency, amount
    )
    print(msg)
    return portfolio


def _handle_get_rate(flags: dict) -> None:
    """Обработать команду get-rate."""
    from_c = flags.get("from", "").strip().upper()
    to_c = flags.get("to", "").strip().upper()

    if not from_c or not to_c:
        print(
            "Использование: get-rate "
            "--from <валюта> --to <валюта>"
        )
        return

    result = usecases.get_rate(from_c, to_c)
    print(result)
