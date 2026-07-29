from __future__ import annotations


def handle_tenant(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts tenant boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_tenant_handler"
    result["shape"] = 4
    return result
