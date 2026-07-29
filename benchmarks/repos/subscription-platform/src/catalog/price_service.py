from __future__ import annotations


def process_price(value: str, *, active: bool = True) -> str:
    """Process catalog price values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"catalog:price:{normalized}"
