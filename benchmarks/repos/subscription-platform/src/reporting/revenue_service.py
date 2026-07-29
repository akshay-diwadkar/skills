from __future__ import annotations


def process_revenue(value: str, *, active: bool = True) -> str:
    """Process reporting revenue values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"reporting:revenue:{normalized}"
