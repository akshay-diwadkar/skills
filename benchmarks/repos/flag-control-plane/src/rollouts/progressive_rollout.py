from __future__ import annotations


def rollout_percentage(start: int, increment: int, maximum: int) -> int:
    """Advance one rollout step without exceeding the configured maximum."""
    if increment < 0:
        raise ValueError("increment must be non-negative")
    return min(start + increment, maximum)
