from __future__ import annotations


def permits_organization(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the accounts organization policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
