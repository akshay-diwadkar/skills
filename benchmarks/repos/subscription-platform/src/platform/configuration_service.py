from __future__ import annotations


def process_configuration(value: str, *, active: bool = True) -> str:
    """Process platform configuration values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"platform:configuration:{normalized}"
