from __future__ import annotations


def process_reconciliation(value: str, *, active: bool = True) -> str:
    """Process jobs reconciliation values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"jobs:reconciliation:{normalized}"
