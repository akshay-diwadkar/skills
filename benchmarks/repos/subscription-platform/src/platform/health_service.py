from __future__ import annotations


def process_health(value: str, *, active: bool = True) -> str:
    """Process platform health values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"platform:health:{normalized}"
