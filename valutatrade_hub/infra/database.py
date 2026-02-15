"""DatabaseManager singleton for JSON file I/O."""

import json
import os

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Singleton that manages reading/writing JSON data files.

    Ensures the data directory exists and provides typed load/save methods.
    """

    _instance = None

    def __new__(cls, *args, **kwargs) -> "DatabaseManager":
        """Ensure only one instance of DatabaseManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: SettingsLoader | None = None) -> None:
        """Initialize with a SettingsLoader instance."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._settings = settings or SettingsLoader()
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Create the data directory if it does not exist."""
        os.makedirs(self._settings.data_dir, exist_ok=True)

    def _read_json(self, path: str, default: object = None) -> object:
        """Read a JSON file and return its contents."""
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except json.JSONDecodeError:
                return default

    def _write_json(self, path: str, data: object) -> None:
        """Write data to a JSON file with pretty formatting."""
        self._ensure_data_dir()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    # ── Users ──────────────────────────────────────────────

    def load_users(self) -> list[dict]:
        """Load the list of registered users."""
        result = self._read_json(self._settings.users_path, default=[])
        return result if isinstance(result, list) else []

    def save_users(self, users: list[dict]) -> None:
        """Save the list of users to disk."""
        self._write_json(self._settings.users_path, users)

    # ── Portfolios ─────────────────────────────────────────

    def load_portfolios(self) -> dict:
        """Load all portfolios keyed by username."""
        result = self._read_json(self._settings.portfolios_path, default={})
        return result if isinstance(result, dict) else {}

    def save_portfolios(self, portfolios: dict) -> None:
        """Save all portfolios to disk."""
        self._write_json(self._settings.portfolios_path, portfolios)

    def load_portfolio(self, username: str) -> dict | None:
        """Load a single portfolio by username."""
        portfolios = self.load_portfolios()
        return portfolios.get(username)

    def save_portfolio(self, username: str, portfolio_data: dict) -> None:
        """Save a single portfolio (merge into the full file)."""
        portfolios = self.load_portfolios()
        portfolios[username] = portfolio_data
        self.save_portfolios(portfolios)

    # ── Rates ──────────────────────────────────────────────

    def load_rates(self) -> dict:
        """Load the current exchange rates."""
        result = self._read_json(
            self._settings.rates_path,
            default={"base": "USD", "rates": {}, "updated_at": None},
        )
        return result if isinstance(result, dict) else {
            "base": "USD", "rates": {}, "updated_at": None
        }

    def save_rates(self, rates_data: dict) -> None:
        """Save the current exchange rates."""
        self._write_json(self._settings.rates_path, rates_data)

    # ── Exchange rates history ─────────────────────────────

    def load_exchange_rates_history(self) -> list[dict]:
        """Load the exchange rates history."""
        result = self._read_json(
            self._settings.exchange_rates_path, default=[]
        )
        return result if isinstance(result, list) else []

    def append_exchange_rates_history(self, entry: dict) -> None:
        """Append a snapshot to the exchange rates history."""
        history = self.load_exchange_rates_history()
        history.append(entry)
        self._write_json(self._settings.exchange_rates_path, history)
