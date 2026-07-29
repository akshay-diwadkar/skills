from __future__ import annotations


def handle_credit(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing credit boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_credit_handler"
    result["shape"] = 4
    return result
