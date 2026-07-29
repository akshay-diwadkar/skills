from __future__ import annotations


def permits_receipt(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the notifications receipt policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
