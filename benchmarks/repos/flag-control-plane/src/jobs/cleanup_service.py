from __future__ import annotations


def process_cleanup(value: str, *, active: bool = True) -> str:
    """Process jobs cleanup values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"jobs:cleanup:{normalized}"
