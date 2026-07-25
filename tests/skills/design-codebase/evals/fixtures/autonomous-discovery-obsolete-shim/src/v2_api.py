"""Canonical v2 API implementation."""


def v2_api_handler(payload: dict) -> dict:
    return {"status": "ok", "result": payload}
