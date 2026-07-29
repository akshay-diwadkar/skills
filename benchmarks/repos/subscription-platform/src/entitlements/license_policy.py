from __future__ import annotations


def permits_license(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the entitlements license policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
