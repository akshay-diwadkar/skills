from __future__ import annotations


def handle_webhook(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications webhook boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_webhook_handler"
    result["shape"] = 3
    return result
