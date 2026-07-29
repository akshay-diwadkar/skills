from __future__ import annotations


def process_environment(value: str, *, active: bool = True) -> str:
    """Process persistence environment values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"persistence:environment:{normalized}"
