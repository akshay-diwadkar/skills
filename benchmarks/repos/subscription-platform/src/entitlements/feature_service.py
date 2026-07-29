from __future__ import annotations


def process_feature(value: str, *, active: bool = True) -> str:
    """Process entitlements feature values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"entitlements:feature:{normalized}"
