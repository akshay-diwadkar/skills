from __future__ import annotations


def permits_rollout(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the jobs rollout policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
