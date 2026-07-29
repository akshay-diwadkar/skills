from __future__ import annotations


def permits_member(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the accounts member policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
