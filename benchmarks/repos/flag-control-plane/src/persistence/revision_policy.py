from __future__ import annotations


def permits_revision(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the persistence revision policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
