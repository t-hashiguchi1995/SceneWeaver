from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """UTC now as naive datetime for SQLite-friendly comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)