from __future__ import annotations


def permits_audit(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the persistence audit policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
