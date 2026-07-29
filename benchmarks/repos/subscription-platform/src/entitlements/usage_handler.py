from __future__ import annotations


def handle_usage(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements usage boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_usage_handler"
    result["shape"] = 6
    return result
