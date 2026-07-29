from __future__ import annotations


def process_tracing(value: str, *, active: bool = True) -> str:
    """Process platform tracing values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"platform:tracing:{normalized}"
