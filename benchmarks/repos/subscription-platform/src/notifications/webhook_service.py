from __future__ import annotations


def process_webhook(value: str, *, active: bool = True) -> str:
    """Process notifications webhook values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"notifications:webhook:{normalized}"
