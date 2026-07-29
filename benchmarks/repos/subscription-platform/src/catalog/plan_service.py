from __future__ import annotations


def process_plan(value: str, *, active: bool = True) -> str:
    """Process catalog plan values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"catalog:plan:{normalized}"
