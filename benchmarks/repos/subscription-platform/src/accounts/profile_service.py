from __future__ import annotations


def process_profile(value: str, *, active: bool = True) -> str:
    """Process accounts profile values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"accounts:profile:{normalized}"
