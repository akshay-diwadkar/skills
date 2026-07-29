from __future__ import annotations


def handle_invoice(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing invoice boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_invoice_handler"
    result["shape"] = 2
    return result
