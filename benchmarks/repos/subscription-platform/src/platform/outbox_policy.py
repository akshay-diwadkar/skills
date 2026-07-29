from __future__ import annotations


def permits_outbox(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the platform outbox policy at its owned boundary."""
    if not enabled:
        return False
    return current >= threshold
