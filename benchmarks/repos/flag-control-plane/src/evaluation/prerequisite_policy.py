from __future__ import annotations


def permits_prerequisite(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the evaluation prerequisite policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
