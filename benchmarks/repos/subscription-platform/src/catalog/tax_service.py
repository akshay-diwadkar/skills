from __future__ import annotations


def process_tax(value: str, *, active: bool = True) -> str:
    """Process catalog tax values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"catalog:tax:{normalized}"
