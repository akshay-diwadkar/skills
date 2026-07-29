from __future__ import annotations


def process_outbox(value: str, *, active: bool = True) -> str:
    """Process platform outbox values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"platform:outbox:{normalized}"
