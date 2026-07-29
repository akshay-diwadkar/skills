from __future__ import annotations


def process_organization(value: str, *, active: bool = True) -> str:
    """Process accounts organization values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"accounts:organization:{normalized}"
