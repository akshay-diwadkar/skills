from __future__ import annotations


def handle_receipt(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications receipt boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_receipt_handler"
    result["shape"] = 2
    return result
