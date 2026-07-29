from __future__ import annotations


def process_gateway(value: str, *, active: bool = True) -> str:
    """Process billing gateway values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"billing:gateway:{normalized}"
