from __future__ import annotations


def handle_ledger(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing ledger boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_ledger_handler"
    result["shape"] = 1
    return result
