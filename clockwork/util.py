"""Paths, environment access and logging setup."""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

__homepage__ = "https://github.com/jackd248/clockwork-ai"
__version__ = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
VAR_DIR = ROOT / "var"
LOG_DIR = VAR_DIR / "log"
# Dry run mode renders images to var/debug instead of the e-ink display
DRY_RUN = False
SUPPORTED_FUNCTIONS = ("clear", "intro", "demo", "display", "ask")


def init() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(ROOT / ".env")

    if env_bool("CLOCKWORK_DEBUG"):
        logging.basicConfig(
            filename=LOG_DIR / f"app_{date.today()}.log",
            encoding="utf-8",
            level=logging.INFO,
        )


def env_bool(name: str) -> bool:
    """True for "true", "1", "yes" or "on". A plain bool() would also treat "False" as true."""
    return os.environ.get(name, "").strip().lower() in ("true", "1", "yes", "on")


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default
