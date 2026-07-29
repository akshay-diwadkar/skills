from __future__ import annotations


def permits_usage(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the reporting usage policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
