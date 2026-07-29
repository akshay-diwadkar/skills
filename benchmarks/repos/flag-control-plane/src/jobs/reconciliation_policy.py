from __future__ import annotations


def permits_reconciliation(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the jobs reconciliation policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
