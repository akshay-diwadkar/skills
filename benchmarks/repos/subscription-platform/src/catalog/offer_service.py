from __future__ import annotations


def process_offer(value: str, *, active: bool = True) -> str:
    """Process catalog offer values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"catalog:offer:{normalized}"
