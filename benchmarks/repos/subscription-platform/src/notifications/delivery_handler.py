from __future__ import annotations


def handle_delivery(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications delivery boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_delivery_handler"
    result["shape"] = 6
    return result
