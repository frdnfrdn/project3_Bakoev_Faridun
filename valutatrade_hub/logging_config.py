"""Настройка логирования: формат, уровень, ротация файлов.

Формат: строковый (человекочитаемый).
Ротация: по размеру файла (1 МБ, до 5 бэкапов).
Уровень по умолчанию: INFO, для отладки — DEBUG.

Пример записи:
    INFO 2025-10-09T12:05:22 BUY user='alice' ...
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> None:
    """Настроить логирование приложения.

    Создаёт директорию логов, файловый обработчик
    с ротацией и форматирование по строковому шаблону.
    Конфигурация берётся из SettingsLoader.
    """
    settings = SettingsLoader()
    log_dir = settings.get("log_dir", "logs")
    log_level = settings.get("log_level", "INFO")

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "actions.log")

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    level = getattr(
        logging, log_level.upper(), logging.INFO
    )
    file_handler.setLevel(level)

    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(file_handler)
