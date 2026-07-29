from __future__ import annotations


def permits_webhook(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the notifications webhook policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
