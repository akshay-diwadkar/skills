from __future__ import annotations


def process_churn(value: str, *, active: bool = True) -> str:
    """Process reporting churn values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"reporting:churn:{normalized}"
