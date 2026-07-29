from __future__ import annotations


def process_percentage(value: str, *, active: bool = True) -> str:
    """Process rollouts percentage values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"rollouts:percentage:{normalized}"
