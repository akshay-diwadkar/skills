from __future__ import annotations


def handle_digest(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications digest boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_digest_handler"
    result["shape"] = 5
    return result
