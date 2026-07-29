from __future__ import annotations


def handle_renewal(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications renewal boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_renewal_handler"
    result["shape"] = 4
    return result
