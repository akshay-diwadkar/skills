from __future__ import annotations


def permits_grant(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the entitlements grant policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
