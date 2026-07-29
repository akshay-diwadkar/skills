from __future__ import annotations


def permits_payment(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the billing payment policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
