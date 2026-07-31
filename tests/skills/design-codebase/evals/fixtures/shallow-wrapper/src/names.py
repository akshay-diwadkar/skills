def canonical_name(value: str) -> str:
    return normalize_name(value)


def normalize_name(value: str) -> str:
    return value.strip().lower()
