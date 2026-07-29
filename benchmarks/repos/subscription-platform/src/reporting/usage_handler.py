from __future__ import annotations


def handle_usage(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting usage boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_usage_handler"
    result["shape"] = 3
    return result
