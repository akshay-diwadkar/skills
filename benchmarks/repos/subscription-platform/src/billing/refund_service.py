from __future__ import annotations


def process_refund(value: str, *, active: bool = True) -> str:
    """Process billing refund values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"billing:refund:{normalized}"
