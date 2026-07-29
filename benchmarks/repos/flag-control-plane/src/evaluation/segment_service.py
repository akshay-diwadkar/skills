from __future__ import annotations


def process_segment(value: str, *, active: bool = True) -> str:
    """Process evaluation segment values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"evaluation:segment:{normalized}"
