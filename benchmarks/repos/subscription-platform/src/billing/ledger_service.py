from __future__ import annotations


def process_ledger(value: str, *, active: bool = True) -> str:
    """Process billing ledger values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"billing:ledger:{normalized}"
