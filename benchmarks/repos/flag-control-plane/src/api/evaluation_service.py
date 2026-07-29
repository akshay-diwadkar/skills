from __future__ import annotations


def process_evaluation(value: str, *, active: bool = True) -> str:
    """Process api evaluation values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"api:evaluation:{normalized}"
