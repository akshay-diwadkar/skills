from __future__ import annotations


def permits_credit(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the billing credit policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
