from __future__ import annotations


def process_clock(value: str, *, active: bool = True) -> str:
    """Process platform clock values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"platform:clock:{normalized}"
