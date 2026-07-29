from __future__ import annotations


def permits_tax(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog tax policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
