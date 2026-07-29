from __future__ import annotations


def permits_currency(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog currency policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
