from __future__ import annotations


def process_flag(value: str, *, active: bool = True) -> str:
    """Process api flag values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"api:flag:{normalized}"
