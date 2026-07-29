from __future__ import annotations


def process_attempt(value: str, *, active: bool = True) -> str:
    """Process billing attempt values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"billing:attempt:{normalized}"
