from __future__ import annotations


def handle_license(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements license boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_license_handler"
    result["shape"] = 3
    return result
