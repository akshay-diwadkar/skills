def current(value: str) -> str:
    normalized = value.strip()
    return normalized.casefold()


def format_label(value: str) -> str:
    return current(value).replace("_", " ").title()
