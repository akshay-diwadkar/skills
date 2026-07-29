from __future__ import annotations


def handle_revenue(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting revenue boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_revenue_handler"
    result["shape"] = 4
    return result
