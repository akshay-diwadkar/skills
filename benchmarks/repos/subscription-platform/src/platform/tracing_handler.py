from __future__ import annotations


def handle_tracing(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one platform tracing boundary payload."""
    result = dict(payload)
    result["handled_by"] = "platform_tracing_handler"
    result["shape"] = 0
    return result
