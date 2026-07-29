from __future__ import annotations


def permits_tenant(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the accounts tenant policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
