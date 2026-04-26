"""Environment parsing helpers for consistent production-safe settings."""
from __future__ import annotations

import os
from typing import Iterable


def get_first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def parse_csv_env(*names: str, default: Iterable[str] | None = None) -> list[str]:
    raw = get_first_env(*names, default="")
    if raw:
        values = [part.strip() for part in raw.split(',') if part.strip()]
        if values:
            return values
    return list(default or [])
