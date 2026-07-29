from __future__ import annotations


def permits_environment(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the api environment policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
