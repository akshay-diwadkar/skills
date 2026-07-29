from __future__ import annotations


def handle_currency(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog currency boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_currency_handler"
    result["shape"] = 1
    return result
