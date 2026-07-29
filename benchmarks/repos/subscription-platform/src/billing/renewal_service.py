from __future__ import annotations


def process_renewal(value: str, *, active: bool = True) -> str:
    """Process billing renewal values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"billing:renewal:{normalized}"
