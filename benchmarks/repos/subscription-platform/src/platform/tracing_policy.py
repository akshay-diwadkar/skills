from __future__ import annotations


def permits_tracing(current: int, threshold: int, *, enabled: bool = True) -> bool:
    """Evaluate the platform tracing policy at its owned boundary."""
    if not enabled:
        return False
    return current > threshold
