from __future__ import annotations


def permits_attempt(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the billing attempt policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
