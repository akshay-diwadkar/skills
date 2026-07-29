from __future__ import annotations


def process_scheduled(value: str, *, active: bool = True) -> str:
    """Process rollouts scheduled values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"rollouts:scheduled:{normalized}"
