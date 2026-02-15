"""Координатор обновления курсов (RatesUpdater).

Получает данные от API-клиентов, объединяет,
сохраняет в историю (exchange_rates.json) и кеш
(rates.json).
"""

import logging
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
)
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
)
from valutatrade_hub.parser_service.storage import (
    RatesStorage,
)

_logger = logging.getLogger("valutatrade_hub.parser")


class RatesUpdater:
    """Точка входа для логики парсинга курсов.

    Координирует вызовы API-клиентов и сохранение.
    Отказоустойчивость: если один клиент падает,
    продолжаем с данными от других.
    """

    def __init__(
        self,
        clients: list[BaseApiClient],
        storage: RatesStorage,
    ):
        """Инициализировать обновлятель.

        Args:
            clients: Список API-клиентов.
            storage: Хранилище курсов.
        """
        self._clients = clients
        self._storage = storage

    def run_update(self) -> dict:
        """Выполнить полный цикл обновления.

        1. Опрашивает каждого клиента.
        2. Объединяет курсы.
        3. Сохраняет в историю и кеш.

        Returns:
            Итоги обновления::

                {
                    'total_rates': int,
                    'errors': list[str],
                    'sources': dict[str, int],
                    'last_refresh': str,
                }
        """
        all_pairs: dict = {}
        history_records: list[dict] = []
        errors: list[str] = []
        sources: dict[str, int] = {}

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for client in self._clients:
            name = client.source_name
            _logger.info(
                "Fetching from %s...", name
            )

            try:
                pairs = client.fetch_rates()
                count = len(pairs)
                sources[name] = count
                _logger.info(
                    "Fetching from %s... OK (%d rates)",
                    name,
                    count,
                )

                for key, info in pairs.items():
                    all_pairs[key] = info
                    record = self._make_record(
                        key, info, now, name
                    )
                    history_records.append(record)

            except ApiRequestError as exc:
                msg = str(exc)
                errors.append(msg)
                _logger.error(
                    "Failed to fetch from %s: %s",
                    name,
                    msg,
                )

        if all_pairs:
            cache_n = self._storage.update_cache(
                all_pairs
            )
            _logger.info(
                "Writing %d rates to rates.json",
                cache_n,
            )

        if history_records:
            hist_n = self._storage.append_history(
                history_records
            )
            _logger.info(
                "Appended %d records to "
                "exchange_rates.json",
                hist_n,
            )

        return {
            "total_rates": len(all_pairs),
            "errors": errors,
            "sources": sources,
            "last_refresh": now,
        }

    @staticmethod
    def _make_record(
        key: str,
        info: dict,
        timestamp: str,
        source: str,
    ) -> dict:
        """Создать запись для журнала.

        id = <FROM>_<TO>_<ISO-UTC timestamp>.
        """
        parts = key.split("_", 1)
        from_cur = parts[0] if parts else key
        to_cur = (
            parts[1] if len(parts) > 1 else "USD"
        )

        return {
            "id": f"{key}_{timestamp}",
            "from_currency": from_cur,
            "to_currency": to_cur,
            "rate": info["rate"],
            "timestamp": timestamp,
            "source": source,
            "meta": info.get("meta", {}),
        }
