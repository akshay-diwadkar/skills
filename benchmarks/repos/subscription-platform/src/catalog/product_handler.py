from __future__ import annotations


def handle_product(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog product boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_product_handler"
    result["shape"] = 0
    return result
