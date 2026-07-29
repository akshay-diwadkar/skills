from __future__ import annotations


def process_rollout(value: str, *, active: bool = True) -> str:
    """Process jobs rollout values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"jobs:rollout:{normalized}"
