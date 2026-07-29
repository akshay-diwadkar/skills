from __future__ import annotations


def permits_renewal(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the billing renewal policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
