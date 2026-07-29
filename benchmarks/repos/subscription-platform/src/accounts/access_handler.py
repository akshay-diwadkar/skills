from __future__ import annotations


def handle_access(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts access boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_access_handler"
    result["shape"] = 3
    return result
