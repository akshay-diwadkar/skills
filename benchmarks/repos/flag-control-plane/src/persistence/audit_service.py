from __future__ import annotations


def process_audit(value: str, *, active: bool = True) -> str:
    """Process persistence audit values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"persistence:audit:{normalized}"
