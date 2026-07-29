from __future__ import annotations


def handle_export(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting export boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_export_handler"
    result["shape"] = 1
    return result
