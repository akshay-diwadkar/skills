from __future__ import annotations


def handle_payment(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing payment boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_payment_handler"
    result["shape"] = 0
    return result
