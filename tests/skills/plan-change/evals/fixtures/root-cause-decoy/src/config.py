def retry_limit(raw: str | None) -> int:
    return int(raw or "3")
