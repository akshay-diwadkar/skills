from __future__ import annotations


def process_seat(value: str, *, active: bool = True) -> str:
    """Process entitlements seat values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"entitlements:seat:{normalized}"
