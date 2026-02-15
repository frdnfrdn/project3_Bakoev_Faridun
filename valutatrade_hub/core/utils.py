"""Вспомогательные функции: JSON I/O, хеширование, генерация ID."""

import hashlib
import json
import os
from datetime import datetime

# ── Пути к файлам данных ─────────────────────────────────

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_HUB_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_ROOT = os.path.dirname(_HUB_DIR)
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

USERS_FILE = os.path.join(DATA_DIR, "users.json")
PORTFOLIOS_FILE = os.path.join(DATA_DIR, "portfolios.json")
RATES_FILE = os.path.join(DATA_DIR, "rates.json")


# ── JSON I/O ─────────────────────────────────────────────


def load_json(filepath: str) -> object:
    """Загрузить данные из JSON-файла.

    Args:
        filepath: Путь к файлу.

    Returns:
        Распарсенные данные или None если файл не найден.
    """
    if not os.path.exists(filepath):
        return None
    with open(filepath, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return None


def save_json(filepath: str, data: object) -> None:
    """Сохранить данные в JSON-файл с форматированием.

    Args:
        filepath: Путь к файлу.
        data: Данные для сохранения.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


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
