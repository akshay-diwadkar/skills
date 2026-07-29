from __future__ import annotations


def process_access(value: str, *, active: bool = True) -> str:
    """Process accounts access values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"accounts:access:{normalized}"
