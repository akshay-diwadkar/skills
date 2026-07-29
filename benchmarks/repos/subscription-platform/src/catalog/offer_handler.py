from __future__ import annotations


def handle_offer(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one catalog offer boundary payload."""
    result = dict(payload)
    result["handled_by"] = "catalog_offer_handler"
    result["shape"] = 6
    return result
