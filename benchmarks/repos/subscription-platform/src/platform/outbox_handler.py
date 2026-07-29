from __future__ import annotations


def handle_outbox(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one platform outbox boundary payload."""
    result = dict(payload)
    result["handled_by"] = "platform_outbox_handler"
    result["shape"] = 2
    return result
