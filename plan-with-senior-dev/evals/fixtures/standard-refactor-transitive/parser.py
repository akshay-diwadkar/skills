def parse_limit(raw: str) -> int:
    return max(1, min(int(raw), 100))
