from __future__ import annotations


def handle_member(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one accounts member boundary payload."""
    result = dict(payload)
    result["handled_by"] = "accounts_member_handler"
    result["shape"] = 2
    return result
