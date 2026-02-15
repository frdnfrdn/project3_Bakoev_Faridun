"""Singleton DatabaseManager — абстракция над JSON-хранилищем.

Централизует все операции чтения/записи data/*.json.
"""

import json
import os

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Управление чтением/записью JSON-файлов данных.

    Реализован через __new__ — аналогично SettingsLoader,
    выбран за простоту и единообразие.
    Гарантирует единственный экземпляр.
    """

    _instance = None

    def __new__(cls) -> "DatabaseManager":
        """Создать или вернуть единственный экземпляр."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализировать с SettingsLoader."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._settings = SettingsLoader()
        self._data_dir = self._settings.get("data_dir")
        os.makedirs(self._data_dir, exist_ok=True)

    def _path(self, filename: str) -> str:
        """Полный путь к файлу в директории данных."""
        return os.path.join(self._data_dir, filename)

    def _read(self, filename: str, default=None):
        """Прочитать JSON-файл.

        Args:
            filename: Имя файла.
            default: Значение при отсутствии/ошибке.
        """
        path = self._path(filename)
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except json.JSONDecodeError:
                return default

    def _write(self, filename: str, data) -> None:
        """Записать данные в JSON-файл.

        Args:
            filename: Имя файла.
            data: Данные для записи.
        """
        path = self._path(filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                data, fh, ensure_ascii=False, indent=2
            )

    # ── Users ─────────────────────────────────────────

    def load_users(self) -> list[dict]:
        """Загрузить список пользователей."""
        result = self._read("users.json", default=[])
        return result if isinstance(result, list) else []

    def save_users(self, users: list[dict]) -> None:
        """Сохранить список пользователей."""
        self._write("users.json", users)

    # ── Portfolios ────────────────────────────────────

    def load_portfolios(self) -> list[dict]:
        """Загрузить все портфели."""
        result = self._read(
            "portfolios.json", default=[]
        )
        return result if isinstance(result, list) else []

    def save_portfolios(
        self, data: list[dict]
    ) -> None:
        """Сохранить все портфели."""
        self._write("portfolios.json", data)

    def load_portfolio(
        self, user_id: int
    ) -> dict | None:
        """Загрузить портфель по user_id."""
        for p in self.load_portfolios():
            if p.get("user_id") == user_id:
                return p
        return None

    def save_portfolio(
        self, portfolio_data: dict
    ) -> None:
        """Сохранить портфель (обновить или добавить)."""
        portfolios = self.load_portfolios()
        uid = portfolio_data.get("user_id")
        updated = False
        for i, p in enumerate(portfolios):
            if p.get("user_id") == uid:
                portfolios[i] = portfolio_data
                updated = True
                break
        if not updated:
            portfolios.append(portfolio_data)
        self.save_portfolios(portfolios)

    # ── Rates ─────────────────────────────────────────

    def load_rates(self) -> dict:
        """Загрузить курсы валют."""
        result = self._read("rates.json", default={})
        return result if isinstance(result, dict) else {}

    def save_rates(self, data: dict) -> None:
        """Сохранить курсы валют."""
        self._write("rates.json", data)
