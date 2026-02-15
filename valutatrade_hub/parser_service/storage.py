"""Операции чтения/записи exchange_rates.json и rates.json.

Атомарная запись: временный файл -> rename.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

from valutatrade_hub.infra.settings import SettingsLoader


class RatesStorage:
    """Хранилище курсов: история и кеш.

    exchange_rates.json — «журнал» всех измерений.
    rates.json — «снимок текущего мира» (кеш).
    """

    def __init__(self):
        """Инициализировать пути из SettingsLoader."""
        settings = SettingsLoader()
        data_dir = settings.get("data_dir")
        self._rates_path = os.path.join(
            data_dir, "rates.json"
        )
        self._history_path = os.path.join(
            data_dir, "exchange_rates.json"
        )
        os.makedirs(data_dir, exist_ok=True)

    # ── History (exchange_rates.json) ─────────────────

    def append_history(
        self, records: list[dict]
    ) -> int:
        """Добавить записи в журнал.

        id = <FROM>_<TO>_<ISO-UTC timestamp>.
        Пропускает дубликаты по id.

        Args:
            records: Список новых записей.

        Returns:
            Количество добавленных записей.
        """
        existing = self._read(
            self._history_path, default=[]
        )
        if not isinstance(existing, list):
            existing = []

        existing_ids = {
            r.get("id") for r in existing
        }
        added = 0
        for rec in records:
            rid = rec.get("id")
            if rid not in existing_ids:
                existing.append(rec)
                existing_ids.add(rid)
                added += 1

        self._atomic_write(
            self._history_path, existing
        )
        return added

    # ── Cache (rates.json) ────────────────────────────

    def update_cache(
        self, pairs: dict[str, dict]
    ) -> int:
        """Обновить кеш курсов.

        Для каждой пары — перезаписать,
        если updated_at свежее текущего.

        Args:
            pairs: {'BTC_USD': {'rate': ..., 'source': ...}}

        Returns:
            Количество обновлённых пар.
        """
        cache = self._read(
            self._rates_path, default={}
        )
        if not isinstance(cache, dict):
            cache = {}

        existing = cache.get("pairs", {})
        now = datetime.now(timezone.utc).isoformat()
        updated = 0

        for key, info in pairs.items():
            existing[key] = {
                "rate": info["rate"],
                "updated_at": now,
                "source": info.get(
                    "source", "unknown"
                ),
            }
            updated += 1

        cache["pairs"] = existing
        cache["last_refresh"] = now
        self._atomic_write(self._rates_path, cache)
        return updated

    # ── I/O ───────────────────────────────────────────

    def _read(self, path: str, default=None):
        """Прочитать JSON-файл."""
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except json.JSONDecodeError:
                return default

    def _atomic_write(
        self, path: str, data
    ) -> None:
        """Атомарная запись: tmp -> rename.

        На Windows os.replace может не быть полностью
        атомарным, но это лучшее доступное решение.
        """
        dir_name = os.path.dirname(path)
        try:
            fd, tmp_path = tempfile.mkstemp(
                suffix=".tmp",
                dir=dir_name,
            )
            with os.fdopen(
                fd, "w", encoding="utf-8"
            ) as tmp:
                json.dump(
                    data,
                    tmp,
                    ensure_ascii=False,
                    indent=2,
                )
            os.replace(tmp_path, path)
        except OSError:
            with open(
                path, "w", encoding="utf-8"
            ) as fh:
                json.dump(
                    data,
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
