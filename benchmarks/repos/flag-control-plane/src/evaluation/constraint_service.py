from __future__ import annotations


def process_constraint(value: str, *, active: bool = True) -> str:
    """Process evaluation constraint values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"evaluation:constraint:{normalized}"
