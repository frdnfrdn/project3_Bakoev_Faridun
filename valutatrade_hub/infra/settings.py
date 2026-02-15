"""Application settings managed by a Singleton SettingsLoader."""

import os


class SettingsLoader:
    """Singleton that centralizes all application settings.

    Provides paths, TTL values, and default configuration.
    """

    _instance = None

    def __new__(cls) -> "SettingsLoader":
        """Ensure only one instance of SettingsLoader exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Load settings on first initialization."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._load_settings()

    def _load_settings(self) -> None:
        """Compute and store all settings."""
        package_dir = os.path.dirname(os.path.abspath(__file__))
        hub_dir = os.path.dirname(package_dir)
        project_root = os.path.dirname(hub_dir)

        self.project_root: str = project_root
        self.data_dir: str = os.path.join(project_root, "data")

        self.users_file: str = "users.json"
        self.portfolios_file: str = "portfolios.json"
        self.rates_file: str = "rates.json"
        self.exchange_rates_file: str = "exchange_rates.json"

        self.rates_ttl: int = 3600
        self.initial_balance: float = 10000.0
        self.base_currency: str = "USD"
        self.api_timeout: int = 10
        self.log_file: str = "app.log"

    @property
    def users_path(self) -> str:
        """Full path to users.json."""
        return os.path.join(self.data_dir, self.users_file)

    @property
    def portfolios_path(self) -> str:
        """Full path to portfolios.json."""
        return os.path.join(self.data_dir, self.portfolios_file)

    @property
    def rates_path(self) -> str:
        """Full path to rates.json."""
        return os.path.join(self.data_dir, self.rates_file)

    @property
    def exchange_rates_path(self) -> str:
        """Full path to exchange_rates.json (history)."""
        return os.path.join(self.data_dir, self.exchange_rates_file)

    @property
    def log_path(self) -> str:
        """Full path to the log file."""
        return os.path.join(self.data_dir, self.log_file)
