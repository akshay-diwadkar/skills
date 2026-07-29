from __future__ import annotations


def process_currency(value: str, *, active: bool = True) -> str:
    """Process catalog currency values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"catalog:currency:{normalized}"
