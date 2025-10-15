from __future__ import annotations

import os
from pathlib import Path

DEFAULT_TARGET_URL = (
    "https://www.stadt-zuerich.ch/de/stadtleben/sport-und-erholung/"
    "sport-und-badeanlagen/hallenbaeder/city.html"
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
DEFAULT_DB_PATH = Path(os.getenv("POOL_LOGGER_DB", "data/guest_logs.db"))
DEFAULT_WS_URL = os.getenv(
    "POOL_LOGGER_WS_URL", "wss://badi-public.crowdmonitor.ch:9591/api"
)


def get_database_url() -> str:
    """Return the SQLAlchemy database URL using the configured path."""

    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def get_target_url() -> str:
    return os.getenv("POOL_LOGGER_TARGET_URL", DEFAULT_TARGET_URL)


def get_user_agent() -> str:
    return os.getenv("POOL_LOGGER_USER_AGENT", DEFAULT_USER_AGENT)


def get_ws_url() -> str:
    """Return the WebSocket URL used to obtain live guest counts."""
    return DEFAULT_WS_URL
