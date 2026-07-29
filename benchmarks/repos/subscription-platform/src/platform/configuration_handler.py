from __future__ import annotations


def handle_configuration(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one platform configuration boundary payload."""
    result = dict(payload)
    result["handled_by"] = "platform_configuration_handler"
    result["shape"] = 5
    return result
