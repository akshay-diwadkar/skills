from __future__ import annotations


def process_flag(value: str, *, active: bool = True) -> str:
    """Process persistence flag values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"persistence:flag:{normalized}"
