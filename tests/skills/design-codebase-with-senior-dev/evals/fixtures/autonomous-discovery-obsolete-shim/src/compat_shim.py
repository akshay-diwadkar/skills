"""Obsolete v1 compatibility shim ready for retirement."""


def legacy_api_wrapper(payload: dict) -> dict:
    # OBSOLETE: all callers migrated to v2_api_handler in release 2.4
    from src.v2_api import v2_api_handler
    return v2_api_handler(payload)
