_cache: dict[str, list[str]] = {}


def load_flags(tenant_id: str, user_id: str) -> list[str]:
    return [f"{tenant_id}:dashboard"]


def flags_for(tenant_id: str, user_id: str) -> list[str]:
    if user_id not in _cache:
        _cache[user_id] = load_flags(tenant_id, user_id)
    return _cache[user_id]
