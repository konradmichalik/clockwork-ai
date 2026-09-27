"""Poem storage and the display lock."""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

import util

STORAGE_DIR = util.VAR_DIR / "storage"
LOCK_FILE = util.ROOT / "display.lock"
# A run that crashed leaves the lock behind, it expires after five minutes
LOCK_TIMEOUT = 300


def _path(directory: Path, clock_time: str) -> Path:
    return directory / clock_time[:2] / f"{clock_time.replace(':', '')}.json"


def _load(path: Path) -> list[str]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except ValueError:
        logging.warning("[storage] Skipping broken file %s", path)
        return []


def write(clock_time: str, poem: str) -> None:
    path = _path(STORAGE_DIR, clock_time)
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[info] Write to storage: {path}")

    # Write to a temporary file first, a power cut mid-write used to leave broken JSON behind
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_load(path) + [poem], indent=4), encoding="utf-8")
    tmp.replace(path)


def read(clock_time: str, directory: Path = STORAGE_DIR) -> str | None:
    poems = _load(_path(directory, clock_time))
    return random.choice(poems) if poems else None


def is_locked() -> bool:
    try:
        age = time.time() - LOCK_FILE.stat().st_mtime
    except FileNotFoundError:
        return False

    if age > LOCK_TIMEOUT:
        unlock()
        return False
    return True


def lock() -> None:
    LOCK_FILE.touch()


def unlock() -> None:
    LOCK_FILE.unlink(missing_ok=True)
