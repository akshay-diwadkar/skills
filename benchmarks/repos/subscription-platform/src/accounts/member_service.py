from __future__ import annotations


def process_member(value: str, *, active: bool = True) -> str:
    """Process accounts member values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"accounts:member:{normalized}"
