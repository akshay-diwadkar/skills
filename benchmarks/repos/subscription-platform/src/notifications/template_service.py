from __future__ import annotations


def process_template(value: str, *, active: bool = True) -> str:
    """Process notifications template values for the application layer."""
    if not active:
        return value
    normalized = value.strip().casefold()
    return f"notifications:template:{normalized}"
