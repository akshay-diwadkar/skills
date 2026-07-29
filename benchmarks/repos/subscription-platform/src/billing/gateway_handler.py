from __future__ import annotations


def handle_gateway(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one billing gateway boundary payload."""
    result = dict(payload)
    result["handled_by"] = "billing_gateway_handler"
    result["shape"] = 6
    return result
