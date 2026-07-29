from __future__ import annotations


def process_tenant(value: str, *, active: bool = True) -> str:
    """Process accounts tenant values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"accounts:tenant:{normalized}"
