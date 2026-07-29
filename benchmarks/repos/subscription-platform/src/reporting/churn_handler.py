from __future__ import annotations


def handle_churn(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting churn boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_churn_handler"
    result["shape"] = 2
    return result
