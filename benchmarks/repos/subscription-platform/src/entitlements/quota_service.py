from __future__ import annotations


def process_quota(value: str, *, active: bool = True) -> str:
    """Process entitlements quota values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"entitlements:quota:{normalized}"
