from __future__ import annotations


def process_product(value: str, *, active: bool = True) -> str:
    """Process catalog product values for the application layer."""
    if not active:
        return value
    normalized = value.strip()
    return f"catalog:product:{normalized}"
