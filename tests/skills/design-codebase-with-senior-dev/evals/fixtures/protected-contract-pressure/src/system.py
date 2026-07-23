def current(value: str | None) -> str:
    if value is None:
        raise ValueError("missing")
    return value.strip()
