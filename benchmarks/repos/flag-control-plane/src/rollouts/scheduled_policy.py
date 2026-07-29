from __future__ import annotations


def permits_scheduled(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the rollouts scheduled policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
