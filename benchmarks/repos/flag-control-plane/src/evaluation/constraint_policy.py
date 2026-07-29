from __future__ import annotations


def permits_constraint(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the evaluation constraint policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
