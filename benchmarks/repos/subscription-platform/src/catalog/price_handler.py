from __future__ import annotations


def handle_price(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog price boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_price_handler"
    result["shape"] = 2
    return result
