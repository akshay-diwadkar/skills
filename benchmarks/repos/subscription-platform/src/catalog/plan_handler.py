from __future__ import annotations


def handle_plan(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog plan boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_plan_handler"
    result["shape"] = 4
    return result
