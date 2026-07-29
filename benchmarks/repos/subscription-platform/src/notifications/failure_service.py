from __future__ import annotations


def process_failure(value: str, *, active: bool = True) -> str:
    """Process notifications failure values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"notifications:failure:{normalized}"
