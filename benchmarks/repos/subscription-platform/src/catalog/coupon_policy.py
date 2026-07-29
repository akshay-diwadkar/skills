from __future__ import annotations


def permits_coupon(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog coupon policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
