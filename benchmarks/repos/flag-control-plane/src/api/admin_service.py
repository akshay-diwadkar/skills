from __future__ import annotations


def process_admin(value: str, *, active: bool = True) -> str:
    """Process api admin values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"api:admin:{normalized}"
