from __future__ import annotations


def process_prerequisite(value: str, *, active: bool = True) -> str:
    """Process evaluation prerequisite values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"evaluation:prerequisite:{normalized}"
