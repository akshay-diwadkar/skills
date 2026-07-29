from __future__ import annotations


def handle_coupon(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog coupon boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_coupon_handler"
    result["shape"] = 5
    return result
