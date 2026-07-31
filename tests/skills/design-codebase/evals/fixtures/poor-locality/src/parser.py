def parse_timeout(raw: str) -> int:
    value = int(raw)
    if value < 0:
        raise ValueError("timeout must be positive")
    return value
