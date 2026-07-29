from __future__ import annotations


def permits_feature(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the entitlements feature policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
