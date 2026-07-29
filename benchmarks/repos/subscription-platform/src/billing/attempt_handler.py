from __future__ import annotations


def handle_attempt(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing attempt boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_attempt_handler"
    result["shape"] = 5
    return result
