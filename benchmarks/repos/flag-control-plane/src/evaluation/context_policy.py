from __future__ import annotations


def permits_context(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the evaluation context policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
