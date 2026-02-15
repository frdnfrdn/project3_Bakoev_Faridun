"""Командный интерфейс (CLI) ValutaTrade Hub.

Поддержка команд с --flag аргументами.
Обработка пользовательских исключений:
- InsufficientFundsError -> текст ошибки как есть.
- CurrencyNotFoundError -> список валют + help.
- ApiRequestError -> совет повторить позже.
"""

import platform
import shlex

from valutatrade_hub.core.currencies import (
    CryptoCurrency,
    get_currency,
    get_supported_codes,
)
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)
from valutatrade_hub.infra.database import (
    DatabaseManager,
)

HELP_TEXT = """
Доступные команды:
  register --username <имя> --password <пароль>
      Регистрация нового пользователя
  login --username <имя> --password <пароль>
      Вход в систему
  show-portfolio [--base <валюта>]
      Показать портфель (требует входа)
  buy --currency <код> --amount <кол-во>
      Купить валюту (требует входа)
  sell --currency <код> --amount <кол-во>
      Продать валюту (требует входа)
  get-rate --from <код> --to <код>
      Показать курс обмена
  update-rates [--source <coingecko|exchangerate>]
      Обновить курсы валют из внешних API
  show-rates [--currency <код>] [--top <N>] [--base <валюта>]
      Показать актуальные курсы из кеша
  currencies
      Список поддерживаемых валют
  help
      Эта справка
  exit
      Выход
""".strip()


def run_cli() -> None:
    """Главный цикл CLI-приложения."""
    print("=== ValutaTrade Hub ===")
    print("Введите 'help' для списка команд.\n")

    current_user: User | None = None
    current_portfolio: Portfolio | None = None

    while True:
        try:
            raw = input("vtHub> ")
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        raw = raw.strip()
        if not raw:
            continue

        cmd, args = _parse_input(raw)

        if cmd == "exit":
            print("До свидания!")
            break
        elif cmd == "help":
            print(HELP_TEXT)
        elif cmd == "currencies":
            _handle_currencies()
        elif cmd == "register":
            _handle_register(args)
        elif cmd == "login":
            current_user, current_portfolio = (
                _handle_login(args)
                or (current_user, current_portfolio)
            )
        elif cmd == "show-portfolio":
            _handle_show_portfolio(
                args, current_user, current_portfolio
            )
        elif cmd == "buy":
            result = _handle_buy(
                args, current_user, current_portfolio
            )
            if result:
                current_portfolio = result
        elif cmd == "sell":
            result = _handle_sell(
                args, current_user, current_portfolio
            )
            if result:
                current_portfolio = result
        elif cmd == "get-rate":
            _handle_get_rate(args)
        elif cmd == "update-rates":
            _handle_update_rates(args)
        elif cmd == "show-rates":
            _handle_show_rates(args)
        else:
            print(
                f"Неизвестная команда: '{cmd}'. "
                "Введите 'help'."
            )


# ── Парсинг ввода ────────────────────────────────────────


def _parse_input(raw: str) -> tuple[str, list[str]]:
    """Разбить строку на команду и аргументы."""
    posix = platform.system() != "Windows"
    try:
        tokens = shlex.split(raw, posix=posix)
    except ValueError:
        tokens = raw.split()
    if not tokens:
        return "", []
    return tokens[0].lower(), tokens[1:]


def _parse_flags(
    args: list[str],
) -> dict[str, str]:
    """Разобрать аргументы вида --key value в словарь."""
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


# ── Проверка авторизации ─────────────────────────────────


def _require_login(
    user: User | None,
    portfolio: Portfolio | None,
) -> bool:
    """Проверить, что пользователь авторизован."""
    if user is None or portfolio is None:
        print(
            "Ошибка: сначала войдите "
            "(login --username ... --password ...)"
        )
        return False
    return True


# ── Обработчики команд ───────────────────────────────────


def _handle_register(args: list[str]) -> None:
    """Обработать команду register."""
    flags = _parse_flags(args)
    username = flags.get("username", "")
    password = flags.get("password", "")

    if not username or not password:
        print(
            "Использование: register "
            "--username <имя> --password <пароль>"
        )
        return

    try:
        msg = register_user(username, password)
        print(msg)
    except ValueError as exc:
        print(f"Ошибка: {exc}")


def _handle_login(
    args: list[str],
) -> tuple[User, Portfolio] | None:
    """Обработать команду login."""
    flags = _parse_flags(args)
    username = flags.get("username", "")
    password = flags.get("password", "")

    if not username or not password:
        print(
            "Использование: login "
            "--username <имя> --password <пароль>"
        )
        return None

    try:
        user, portfolio = login_user(
            username, password
        )
        print(
            f"Добро пожаловать, {user.username}! "
            f"(id={user.user_id})"
        )
        return user, portfolio
    except ValueError as exc:
        print(f"Ошибка: {exc}")
        return None


def _handle_show_portfolio(
    args: list[str],
    user: User | None,
    portfolio: Portfolio | None,
) -> None:
    """Обработать команду show-portfolio."""
    if not _require_login(user, portfolio):
        return

    flags = _parse_flags(args)
    base = flags.get("base", "USD").upper()

    print(show_portfolio(user, portfolio, base))


def _handle_buy(
    args: list[str],
    user: User | None,
    portfolio: Portfolio | None,
) -> Portfolio | None:
    """Обработать команду buy."""
    if not _require_login(user, portfolio):
        return None

    flags = _parse_flags(args)
    currency = flags.get("currency", "")
    amount_str = flags.get("amount", "")

    if not currency or not amount_str:
        print(
            "Использование: buy "
            "--currency <код> --amount <кол-во>"
        )
        return None

    try:
        amount = float(amount_str)
    except ValueError:
        print(f"Ошибка: '{amount_str}' не число")
        return None

    try:
        updated, msg = buy_currency(
            portfolio, currency, amount
        )
        print(msg)
        return updated
    except CurrencyNotFoundError as exc:
        _print_currency_error(exc)
        return None
    except InsufficientFundsError as exc:
        print(f"Ошибка: {exc}")
        return None
    except ValueError as exc:
        print(f"Ошибка: {exc}")
        return None


def _handle_sell(
    args: list[str],
    user: User | None,
    portfolio: Portfolio | None,
) -> Portfolio | None:
    """Обработать команду sell."""
    if not _require_login(user, portfolio):
        return None

    flags = _parse_flags(args)
    currency = flags.get("currency", "")
    amount_str = flags.get("amount", "")

    if not currency or not amount_str:
        print(
            "Использование: sell "
            "--currency <код> --amount <кол-во>"
        )
        return None

    try:
        amount = float(amount_str)
    except ValueError:
        print(f"Ошибка: '{amount_str}' не число")
        return None

    try:
        updated, msg = sell_currency(
            portfolio, currency, amount
        )
        print(msg)
        return updated
    except CurrencyNotFoundError as exc:
        _print_currency_error(exc)
        return None
    except InsufficientFundsError as exc:
        print(f"Ошибка: {exc}")
        return None
    except ValueError as exc:
        print(f"Ошибка: {exc}")
        return None


def _handle_get_rate(args: list[str]) -> None:
    """Обработать команду get-rate."""
    flags = _parse_flags(args)
    from_cur = flags.get("from", "")
    to_cur = flags.get("to", "")

    if not from_cur or not to_cur:
        print(
            "Использование: get-rate "
            "--from <код> --to <код>"
        )
        return

    try:
        print(get_rate(from_cur, to_cur))
    except CurrencyNotFoundError as exc:
        _print_currency_error(exc)
    except ApiRequestError as exc:
        print(f"Ошибка: {exc}")
        print(
            "Повторите попытку позже "
            "или проверьте сеть."
        )
    except ValueError as exc:
        print(f"Ошибка: {exc}")


def _handle_update_rates(args: list[str]) -> None:
    """Обработать команду update-rates.

    Запуск немедленного обновления курсов
    из внешних API (CoinGecko, ExchangeRate-API).
    """
    from valutatrade_hub.parser_service.api_clients import (
        CoinGeckoClient,
        ExchangeRateApiClient,
    )
    from valutatrade_hub.parser_service.config import (
        ParserConfig,
    )
    from valutatrade_hub.parser_service.storage import (
        RatesStorage,
    )
    from valutatrade_hub.parser_service.updater import (
        RatesUpdater,
    )

    flags = _parse_flags(args)
    source = flags.get("source", "").lower()

    config = ParserConfig()
    storage = RatesStorage()

    clients = []
    if not source or source == "coingecko":
        clients.append(CoinGeckoClient(config))
    if not source or source == "exchangerate":
        clients.append(
            ExchangeRateApiClient(config)
        )

    if not clients:
        print(
            "Неизвестный источник. "
            "Допустимые: coingecko, exchangerate"
        )
        return

    print("INFO: Starting rates update...")

    updater = RatesUpdater(clients, storage)
    result = updater.run_update()

    for name, count in result["sources"].items():
        print(
            f"INFO: Fetching from {name}... "
            f"OK ({count} rates)"
        )
    for error in result["errors"]:
        print(f"ERROR: {error}")

    total = result["total_rates"]
    if total:
        print(
            f"INFO: Writing {total} rates "
            "to data/rates.json..."
        )
        print(
            f"Update successful. "
            f"Total rates updated: {total}. "
            f"Last refresh: "
            f"{result['last_refresh']}"
        )
    elif result["errors"]:
        print(
            "Update completed with errors. "
            "Check logs/actions.log for details."
        )
    else:
        print("No rates updated.")


def _handle_show_rates(args: list[str]) -> None:
    """Обработать команду show-rates.

    Показать актуальные курсы из локального кеша
    с фильтрацией по валюте, top-N, базовой валюте.
    """
    flags = _parse_flags(args)
    currency_filter = flags.get(
        "currency", ""
    ).upper()
    top_str = flags.get("top", "")
    base = flags.get("base", "USD").upper()

    db = DatabaseManager()
    rates = db.load_rates()
    pairs = rates.get("pairs", {})
    last_refresh = rates.get(
        "last_refresh", "неизвестно"
    )

    if not pairs:
        print(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', "
            "чтобы загрузить данные."
        )
        return

    # Фильтр по валюте
    if currency_filter:
        filtered = {
            k: v
            for k, v in pairs.items()
            if currency_filter in k
        }
        if not filtered:
            print(
                f"Курс для '{currency_filter}' "
                "не найден в кеше."
            )
            return
        pairs = filtered

    # Конвертация в другую базу
    display = _build_display_pairs(
        pairs, base
    )

    # Фильтр --top (только крипто)
    if top_str:
        display = _filter_top(display, top_str)

    # Сортировка по убыванию курса
    items = sorted(
        display.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    print(
        f"Rates from cache "
        f"(updated at {last_refresh}):"
    )
    for key, rate_val in items:
        print(f"  - {key}: {_fmt_display(rate_val)}")


def _handle_currencies() -> None:
    """Показать список поддерживаемых валют."""
    codes = get_supported_codes()
    print(
        "Поддерживаемые валюты: "
        + ", ".join(codes)
    )


# ── Вспомогательные ──────────────────────────────────────


def _print_currency_error(
    exc: CurrencyNotFoundError,
) -> None:
    """Вывести ошибку о неизвестной валюте."""
    print(f"Ошибка: {exc}")
    codes = get_supported_codes()
    print(
        "Поддерживаемые валюты: "
        + ", ".join(codes)
    )
    print(
        "Используйте 'get-rate --from <код> "
        "--to <код>' для проверки курса."
    )


def _build_display_pairs(
    pairs: dict, base: str
) -> dict[str, float]:
    """Собрать пары для отображения.

    Если base != USD, конвертирует через кросс-курс.
    """
    if base == "USD":
        return {
            k: v["rate"] for k, v in pairs.items()
        }

    # Найти курс базовой валюты к USD
    base_key = f"{base}_USD"
    base_rate = None
    for k, v in pairs.items():
        if k == base_key:
            base_rate = v["rate"]
            break

    if not base_rate:
        return {
            k: v["rate"] for k, v in pairs.items()
        }

    result = {}
    for key, info in pairs.items():
        parts = key.split("_")
        from_cur = parts[0]
        if from_cur == base:
            continue
        rate_base = info["rate"] / base_rate
        result[f"{from_cur}_{base}"] = rate_base

    return result


def _filter_top(
    display: dict[str, float], top_str: str
) -> dict[str, float]:
    """Отфильтровать top-N криптовалют."""
    try:
        n = int(top_str)
    except ValueError:
        return display

    crypto_pairs = {}
    for key, rate_val in display.items():
        code = key.split("_")[0]
        try:
            curr = get_currency(code)
            if isinstance(curr, CryptoCurrency):
                crypto_pairs[key] = rate_val
        except CurrencyNotFoundError:
            pass

    top = dict(
        sorted(
            crypto_pairs.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:n]
    )
    return top


def _fmt_display(rate_val: float) -> str:
    """Форматировать курс для отображения."""
    if rate_val >= 1:
        return f"{rate_val:.2f}"
    return f"{rate_val:.5f}"
