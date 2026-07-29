from __future__ import annotations


def permits_variant(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the evaluation variant policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
