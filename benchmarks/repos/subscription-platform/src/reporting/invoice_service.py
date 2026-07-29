from __future__ import annotations


def process_invoice(value: str, *, active: bool = True) -> str:
    """Process reporting invoice values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"reporting:invoice:{normalized}"
