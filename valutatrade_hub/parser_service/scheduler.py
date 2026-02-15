"""Планировщик периодического обновления курсов.

Запускает RatesUpdater по таймеру в фоновом потоке.
"""

import logging
import threading

from valutatrade_hub.parser_service.updater import (
    RatesUpdater,
)

_logger = logging.getLogger(
    "valutatrade_hub.scheduler"
)


class Scheduler:
    """Периодический запуск обновления курсов.

    Usage::

        scheduler = Scheduler(updater, interval=300)
        scheduler.start()
        # ... приложение работает ...
        scheduler.stop()
    """

    def __init__(
        self,
        updater: RatesUpdater,
        interval_seconds: int = 300,
    ):
        """Инициализировать планировщик.

        Args:
            updater: Экземпляр RatesUpdater.
            interval_seconds: Интервал (секунды).
        """
        self._updater = updater
        self._interval = interval_seconds
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        """Запустить периодическое обновление."""
        if self._running:
            _logger.warning(
                "Scheduler already running"
            )
            return
        self._running = True
        _logger.info(
            "Scheduler started (interval=%ds)",
            self._interval,
        )
        self._schedule_next()

    def stop(self) -> None:
        """Остановить планировщик."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        _logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Проверить, запущен ли планировщик."""
        return self._running

    def _schedule_next(self) -> None:
        """Запланировать следующее обновление."""
        if not self._running:
            return
        self._timer = threading.Timer(
            self._interval, self._tick
        )
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        """Выполнить одно обновление."""
        if not self._running:
            return
        try:
            result = self._updater.run_update()
            _logger.info(
                "Scheduled update: %d rates",
                result.get("total_rates", 0),
            )
        except Exception as exc:
            _logger.error(
                "Scheduled update failed: %s", exc
            )
        self._schedule_next()
