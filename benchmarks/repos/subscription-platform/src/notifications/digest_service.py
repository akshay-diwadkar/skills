from __future__ import annotations


def process_digest(value: str, *, active: bool = True) -> str:
    """Process notifications digest values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"notifications:digest:{normalized}"
