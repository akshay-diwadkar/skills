from __future__ import annotations


def permits_regional(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the rollouts regional policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
