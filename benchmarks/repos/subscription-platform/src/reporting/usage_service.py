from __future__ import annotations


def process_usage(value: str, *, active: bool = True) -> str:
    """Process reporting usage values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"reporting:usage:{normalized}"
