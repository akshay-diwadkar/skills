from __future__ import annotations


def permits_export(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the reporting export policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
