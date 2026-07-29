from __future__ import annotations


def handle_seat(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one entitlements seat boundary payload."""
    result = dict(payload)
    result["handled_by"] = "entitlements_seat_handler"
    result["shape"] = 1
    return result
