from __future__ import annotations


def handle_feature(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements feature boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_feature_handler"
    result["shape"] = 0
    return result
