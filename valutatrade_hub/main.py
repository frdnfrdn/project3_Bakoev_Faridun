"""Entry point for ValutaTrade Hub."""

from valutatrade_hub.cli.interface import run_cli
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging


def main() -> None:
    """Initialize logging and start the CLI."""
    settings = SettingsLoader()
    setup_logging(settings.log_path)
    run_cli()


if __name__ == "__main__":
    main()
