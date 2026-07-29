from __future__ import annotations


def process_idempotency(value: str, *, active: bool = True) -> str:
    """Process platform idempotency values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"platform:idempotency:{normalized}"
