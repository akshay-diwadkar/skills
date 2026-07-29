from __future__ import annotations


def handle_identity(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts identity boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_identity_handler"
    result["shape"] = 6
    return result
