def normalize_name(value: str | None) -> str:
    return value.strip() if value is not None else ""
