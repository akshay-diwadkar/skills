from __future__ import annotations


def handle_template(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one notifications template boundary payload."""
    result = dict(payload)
    result["handled_by"] = "notifications_template_handler"
    result["shape"] = 1
    return result
