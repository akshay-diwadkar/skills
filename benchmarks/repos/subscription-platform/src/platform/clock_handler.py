from __future__ import annotations


def handle_clock(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one platform clock boundary payload."""
    result = dict(payload)
    result["handled_by"] = "platform_clock_handler"
    result["shape"] = 6
    return result
