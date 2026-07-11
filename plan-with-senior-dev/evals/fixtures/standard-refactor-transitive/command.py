from api import parse_limit


def run(raw_limit: str) -> int:
    return parse_limit(raw_limit)
