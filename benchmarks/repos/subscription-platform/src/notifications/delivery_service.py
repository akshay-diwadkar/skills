from __future__ import annotations


def process_delivery(value: str, *, active: bool = True) -> str:
    """Process notifications delivery values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"notifications:delivery:{normalized}"
