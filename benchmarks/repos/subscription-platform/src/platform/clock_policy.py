from __future__ import annotations


def permits_clock(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the platform clock policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
