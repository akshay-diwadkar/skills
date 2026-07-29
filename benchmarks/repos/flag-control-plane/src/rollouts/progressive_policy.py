from __future__ import annotations


def permits_progressive(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the rollouts progressive policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
