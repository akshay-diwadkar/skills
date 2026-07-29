from __future__ import annotations


def handle_session(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts session boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_session_handler"
    result["shape"] = 1
    return result
