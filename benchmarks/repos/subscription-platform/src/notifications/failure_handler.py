from __future__ import annotations


def handle_failure(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications failure boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_failure_handler"
    result["shape"] = 0
    return result
