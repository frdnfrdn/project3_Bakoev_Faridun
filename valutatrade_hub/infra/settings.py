"""Singleton SettingsLoader — единая точка конфигурации.

Ответственность: загрузка/кеширование конфигурации проекта.
Параметры: пути к data/, TTL курсов, дефолтная валюта,
путь к логам, формат логов.
"""

import os


class SettingsLoader:
    """Загрузка и кеширование конфигурации проекта.

    Реализован через __new__ — выбран за простоту и
    читабельность по сравнению с метаклассами.
    Гарантирует единственный экземпляр при любых импортах.

    Ключи конфигурации:
        project_root — корневая директория проекта
        data_dir — путь к директории с JSON-файлами
        log_dir — путь к директории логов
        rates_ttl_seconds — время жизни кеша курсов
        default_base_currency — базовая валюта по умолч.
        log_level — уровень логирования (INFO/DEBUG)
        log_format — формат логов (string/json)
    """

    _instance = None

    def __new__(cls) -> "SettingsLoader":
        """Создать или вернуть единственный экземпляр."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Загрузить конфигурацию при первом создании."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._load_config()

    def _load_config(self) -> None:
        """Вычислить и сохранить параметры конфигурации."""
        _this = os.path.dirname(os.path.abspath(__file__))
        _hub = os.path.dirname(_this)
        _root = os.path.dirname(_hub)

        self._config: dict = {
            "project_root": _root,
            "data_dir": os.path.join(_root, "data"),
            "log_dir": os.path.join(_root, "logs"),
            "users_file": "users.json",
            "portfolios_file": "portfolios.json",
            "rates_file": "rates.json",
            "rates_ttl_seconds": 604800,
            "default_base_currency": "USD",
            "log_level": "INFO",
            "log_format": "string",
        }

    def get(self, key: str, default=None):
        """Получить значение параметра.

        Args:
            key: Ключ конфигурации.
            default: Значение по умолчанию.

        Returns:
            Значение параметра или default.
        """
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перезагрузить конфигурацию."""
        self._load_config()
