from __future__ import annotations


def handle_tax(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog tax boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_tax_handler"
    result["shape"] = 3
    return result
