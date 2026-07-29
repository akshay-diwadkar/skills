from __future__ import annotations


def process_regional(value: str, *, active: bool = True) -> str:
    """Process rollouts regional values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"rollouts:regional:{normalized}"
