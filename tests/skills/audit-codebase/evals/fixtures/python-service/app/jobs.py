from __future__ import annotations

from .config import DEFAULT_RETRIES


def attempts_for(retries: int | None) -> int:
    effective_retries = retries or DEFAULT_RETRIES
    return effective_retries + 1
