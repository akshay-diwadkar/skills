from __future__ import annotations


def permits_plan(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog plan policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
