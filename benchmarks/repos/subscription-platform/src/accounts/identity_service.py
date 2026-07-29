from __future__ import annotations


def process_identity(value: str, *, active: bool = True) -> str:
    """Process accounts identity values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"accounts:identity:{normalized}"
