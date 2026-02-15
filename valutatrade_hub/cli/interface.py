"""CLI interface: command loop and handlers for ValutaTrade Hub."""

import shlex
import sys

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    RatesExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValutaTradeError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_portfolio_info,
    get_rate,
    login_user,
    register_user,
    sell_currency,
)
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater

HELP_TEXT = """
Available commands:
  register <username> <password>  - Register a new account
  login <username> <password>     - Log in to your account
  logout                          - Log out
  show-portfolio                  - Display your portfolio
  buy <currency> <amount>         - Buy currency using USD
  sell <currency> <amount>        - Sell currency for USD
  get-rate <currency>             - Show exchange rate for a currency
  update-rates                    - Fetch latest rates from APIs
  show-rates                      - Show all current exchange rates
  help                            - Show this help message
  exit / quit                     - Exit the application
""".strip()


def _parse_command(raw: str) -> tuple[str, list[str]]:
    """Parse a raw input string into command and arguments.

    Uses shlex.split with posix=False on Windows for compatibility.
    """
    posix = sys.platform != "win32"
    parts = shlex.split(raw, posix=posix)
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def _require_login(
    user: User | None, portfolio: Portfolio | None
) -> tuple[User, Portfolio]:
    """Check that a user is logged in.

    Raises:
        ValutaTradeError: If not logged in.
    """
    if user is None or portfolio is None:
        raise ValutaTradeError(
            "You must log in first. Use: login <username> <password>"
        )
    return user, portfolio


# ── Command Handlers ──────────────────────────────────────


def handle_register(
    args: list[str],
    db: DatabaseManager,
    settings: SettingsLoader,
) -> tuple[User, Portfolio]:
    """Handle the 'register' command."""
    if len(args) < 2:
        print("Usage: register <username> <password>")
        raise ValueError("Missing arguments")
    username, password = args[0], args[1]
    user, portfolio = register_user(username, password, db, settings)
    print(f"User '{username}' registered successfully!")
    print(f"Starting balance: {settings.initial_balance:.2f} {settings.base_currency}")
    return user, portfolio


def handle_login(
    args: list[str],
    db: DatabaseManager,
) -> tuple[User, Portfolio]:
    """Handle the 'login' command."""
    if len(args) < 2:
        print("Usage: login <username> <password>")
        raise ValueError("Missing arguments")
    username, password = args[0], args[1]
    user, portfolio = login_user(username, password, db)
    print(f"Welcome back, {username}!")
    return user, portfolio


def handle_show_portfolio(
    user: User | None,
    portfolio: Portfolio | None,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> None:
    """Handle the 'show-portfolio' command."""
    user, portfolio = _require_login(user, portfolio)
    info = get_portfolio_info(portfolio, db, settings)

    table = PrettyTable()
    table.field_names = ["Currency", "Balance", "Value (USD)"]
    table.align["Currency"] = "l"
    table.align["Balance"] = "r"
    table.align["Value (USD)"] = "r"

    for w in info["wallets"]:
        table.add_row([
            w["currency"],
            f"{w['balance']:.4f}",
            f"{w['value_usd']:.2f}",
        ])

    print(f"\nPortfolio for {info['username']}:")
    print(table)
    print(f"Total value: {info['total_value_usd']:.2f} USD")
    print(f"Rates updated: {info['rates_updated_at']}")


def handle_buy(
    args: list[str],
    user: User | None,
    portfolio: Portfolio | None,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> Portfolio:
    """Handle the 'buy' command."""
    user, portfolio = _require_login(user, portfolio)
    if len(args) < 2:
        print("Usage: buy <currency> <amount>")
        raise ValueError("Missing arguments")

    currency = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        raise ValueError(f"Invalid amount: '{args[1]}'") from None

    result = buy_currency(portfolio, currency, amount, db, settings)
    print(result)
    return portfolio


def handle_sell(
    args: list[str],
    user: User | None,
    portfolio: Portfolio | None,
    db: DatabaseManager,
    settings: SettingsLoader,
) -> Portfolio:
    """Handle the 'sell' command."""
    user, portfolio = _require_login(user, portfolio)
    if len(args) < 2:
        print("Usage: sell <currency> <amount>")
        raise ValueError("Missing arguments")

    currency = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        raise ValueError(f"Invalid amount: '{args[1]}'") from None

    result = sell_currency(portfolio, currency, amount, db, settings)
    print(result)
    return portfolio


def handle_get_rate(
    args: list[str],
    db: DatabaseManager,
    settings: SettingsLoader,
) -> None:
    """Handle the 'get-rate' command."""
    if len(args) < 1:
        print("Usage: get-rate <currency>")
        raise ValueError("Missing arguments")

    info = get_rate(args[0], db, settings)
    print(
        f"1 {info['currency']} = {info['rate_usd']:.4f} {info['base']}  "
        f"(updated: {info['updated_at']})"
    )


def handle_update_rates(settings: SettingsLoader) -> None:
    """Handle the 'update-rates' command."""
    print("Fetching latest exchange rates...")
    updater = RatesUpdater(settings)
    rates = updater.run_update()
    print(f"Updated {len(rates)} exchange rates successfully!")


def handle_show_rates(
    db: DatabaseManager,
) -> None:
    """Handle the 'show-rates' command."""
    rates_data = db.load_rates()
    rates = rates_data.get("rates", {})
    updated_at = rates_data.get("updated_at", "N/A")

    if not rates:
        print("No rates available. Run 'update-rates' first.")
        return

    table = PrettyTable()
    table.field_names = ["Currency", "1 Unit = USD"]
    table.align["Currency"] = "l"
    table.align["1 Unit = USD"] = "r"

    for currency in sorted(rates.keys()):
        table.add_row([currency, f"{rates[currency]:.4f}"])

    print(f"\nExchange Rates (base: USD, updated: {updated_at}):")
    print(table)


# ── Main CLI Loop ─────────────────────────────────────────


def run_cli() -> None:
    """Run the interactive command-line interface."""
    settings = SettingsLoader()
    db = DatabaseManager(settings)

    current_user: User | None = None
    current_portfolio: Portfolio | None = None

    print("=" * 50)
    print("  Welcome to ValutaTrade Hub!")
    print("  Type 'help' for available commands.")
    print("=" * 50)

    while True:
        try:
            prompt = (
                f"[{current_user.username}] " if current_user else ""
            )
            raw = input(f"\n{prompt}ValutaTrade> ").strip()
            if not raw:
                continue

            command, args = _parse_command(raw)

            if command in ("exit", "quit"):
                print("Goodbye!")
                break
            elif command == "help":
                print(HELP_TEXT)
            elif command == "register":
                current_user, current_portfolio = handle_register(
                    args, db, settings
                )
            elif command == "login":
                current_user, current_portfolio = handle_login(args, db)
            elif command == "logout":
                current_user = None
                current_portfolio = None
                print("Logged out successfully.")
            elif command == "show-portfolio":
                handle_show_portfolio(
                    current_user, current_portfolio, db, settings
                )
            elif command == "buy":
                current_portfolio = handle_buy(
                    args, current_user, current_portfolio, db, settings
                )
            elif command == "sell":
                current_portfolio = handle_sell(
                    args, current_user, current_portfolio, db, settings
                )
            elif command == "get-rate":
                handle_get_rate(args, db, settings)
            elif command == "update-rates":
                handle_update_rates(settings)
            elif command == "show-rates":
                handle_show_rates(db)
            else:
                print(
                    f"Unknown command: '{command}'. "
                    "Type 'help' for available commands."
                )

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except (
            InsufficientFundsError,
            CurrencyNotFoundError,
            UserNotFoundError,
            UserAlreadyExistsError,
            AuthenticationError,
            RatesExpiredError,
            ApiRequestError,
        ) as exc:
            print(f"Error: {exc}")
        except ValueError as exc:
            print(f"Input error: {exc}")
        except ValutaTradeError as exc:
            print(f"Error: {exc}")
