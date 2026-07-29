from __future__ import annotations


def handle_refund(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing refund boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_refund_handler"
    result["shape"] = 3
    return result
