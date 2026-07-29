from __future__ import annotations


def handle_quota(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements quota boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_quota_handler"
    result["shape"] = 5
    return result
