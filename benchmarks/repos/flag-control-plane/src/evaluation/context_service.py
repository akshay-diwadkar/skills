from __future__ import annotations


def process_context(value: str, *, active: bool = True) -> str:
    """Process evaluation context values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"evaluation:context:{normalized}"
