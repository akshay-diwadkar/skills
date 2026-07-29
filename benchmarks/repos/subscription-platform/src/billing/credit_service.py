from __future__ import annotations


def process_credit(value: str, *, active: bool = True) -> str:
    """Process billing credit values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"billing:credit:{normalized}"
