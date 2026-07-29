from __future__ import annotations


def permits_emergency(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the rollouts emergency policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
