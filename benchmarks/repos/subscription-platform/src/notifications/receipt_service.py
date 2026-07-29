from __future__ import annotations


def process_receipt(value: str, *, active: bool = True) -> str:
    """Process notifications receipt values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"notifications:receipt:{normalized}"
