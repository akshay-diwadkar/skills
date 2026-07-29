from __future__ import annotations


def handle_invoice(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting invoice boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_invoice_handler"
    result["shape"] = 5
    return result
