"""Вспомогательные функции: хеширование, генерация ID, форматирование.

Валидация валютных кодов, конвертации.
JSON I/O перенесён в infra/database.py.
"""

import hashlib
import os
from datetime import datetime

# ── Хеширование паролей ──────────────────────────────────


def generate_salt() -> str:
    """Сгенерировать случайную соль для хеширования."""
    return os.urandom(16).hex()


def hash_password(password: str, salt: str) -> str:
    """Захешировать пароль с солью через SHA-256.

    Args:
        password: Пароль в открытом виде.
        salt: Уникальная соль пользователя.

    Returns:
        Хеш-строка в hex-формате.
    """
    return hashlib.sha256(
        (password + salt).encode("utf-8")
    ).hexdigest()


# ── Генерация ID ─────────────────────────────────────────


def get_next_user_id(users: list[dict]) -> int:
    """Получить следующий user_id (автоинкремент).

    Args:
        users: Список словарей пользователей.

    Returns:
        Следующий свободный ID.
    """
    if not users:
        return 1
    return max(u.get("user_id", 0) for u in users) + 1


# ── Форматирование ───────────────────────────────────────


def format_datetime(iso_str: str | None) -> str:
    """Форматировать ISO datetime для отображения.

    Args:
        iso_str: Строка в ISO-формате.

    Returns:
        Строка вида 'YYYY-MM-DD HH:MM:SS'.
    """
    if not iso_str:
        return "неизвестно"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(iso_str)


# ── Валидация ────────────────────────────────────────────


def validate_currency_code(code: str) -> str:
    """Валидировать и нормализовать код валюты.

    Args:
        code: Код валюты.

    Returns:
        Код в верхнем регистре.

    Raises:
        ValueError: Если код некорректен.
    """
    if not code or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    code = code.strip().upper()
    if len(code) < 2 or len(code) > 5:
        raise ValueError("Код валюты: 2-5 символов")
    if " " in code:
        raise ValueError(
            "Код валюты не может содержать пробелы"
        )
    return code
