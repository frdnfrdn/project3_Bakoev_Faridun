"""Atomic file storage for exchange rates."""

import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def atomic_write_json(path: str, data: object) -> None:
    """Write JSON data atomically using tmp-file + rename.

    This prevents data corruption if the process crashes mid-write.

    Args:
        path: Target file path.
        data: JSON-serializable data to write.
    """
    dir_name = os.path.dirname(path)
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=dir_name, suffix=".tmp", prefix=".rates_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        if os.path.exists(path):
            os.replace(tmp_path, path)
        else:
            os.rename(tmp_path, path)
        logger.info("Atomically wrote data to %s", path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
