from __future__ import annotations


def handle_organization(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts organization boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_organization_handler"
    result["shape"] = 0
    return result
