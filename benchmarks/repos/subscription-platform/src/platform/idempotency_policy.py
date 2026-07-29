from __future__ import annotations


def permits_idempotency(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the platform idempotency policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
