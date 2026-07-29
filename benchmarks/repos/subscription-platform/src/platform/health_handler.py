from __future__ import annotations


def handle_health(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one platform health boundary payload."""
    result = dict(payload)
    result["handled_by"] = "platform_health_handler"
    result["shape"] = 3
    return result
