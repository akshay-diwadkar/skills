def fetch(key: str) -> str | None:
    return "cached" if key in {"hot"} else None
