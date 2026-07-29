from __future__ import annotations


def permits_digest(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the notifications digest policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
