from __future__ import annotations


def permits_admin(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the api admin policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
