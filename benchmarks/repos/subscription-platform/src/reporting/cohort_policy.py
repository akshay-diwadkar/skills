from __future__ import annotations


def permits_cohort(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the reporting cohort policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
