from __future__ import annotations


def permits_gateway(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the billing gateway policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
