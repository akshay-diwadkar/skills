from __future__ import annotations


def permits_product(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the catalog product policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
