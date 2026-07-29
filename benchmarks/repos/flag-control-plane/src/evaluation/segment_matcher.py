from __future__ import annotations


def matches_segment(attributes: dict[str, str], required: dict[str, str]) -> bool:
    """Return whether every required attribute is present with the expected value."""
    return all(attributes.get(key) == value for key, value in required.items())
