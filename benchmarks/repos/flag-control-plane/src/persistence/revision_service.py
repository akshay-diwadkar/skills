from __future__ import annotations


def process_revision(value: str, *, active: bool = True) -> str:
    """Process persistence revision values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"persistence:revision:{normalized}"
