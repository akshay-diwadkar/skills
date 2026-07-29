from __future__ import annotations


def permits_price(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog price policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
