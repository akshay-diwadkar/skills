from __future__ import annotations


def handle_profile(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts profile boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_profile_handler"
    result["shape"] = 5
    return result
