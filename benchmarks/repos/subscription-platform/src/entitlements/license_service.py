from __future__ import annotations


def process_license(value: str, *, active: bool = True) -> str:
    """Process entitlements license values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"entitlements:license:{normalized}"
