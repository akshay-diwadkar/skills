from __future__ import annotations


def permits_seat(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the entitlements seat policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
