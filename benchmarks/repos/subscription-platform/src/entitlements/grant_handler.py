from __future__ import annotations


def handle_grant(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements grant boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_grant_handler"
    result["shape"] = 2
    return result
