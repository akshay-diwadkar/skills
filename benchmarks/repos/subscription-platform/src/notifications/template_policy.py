from __future__ import annotations


def permits_template(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the notifications template policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
