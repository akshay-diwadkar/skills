from __future__ import annotations


def permits_churn(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the reporting churn policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
