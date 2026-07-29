from __future__ import annotations


def permits_session(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the accounts session policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
