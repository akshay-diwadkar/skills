from __future__ import annotations


def process_variant(value: str, *, active: bool = True) -> str:
    """Process evaluation variant values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"evaluation:variant:{normalized}"
