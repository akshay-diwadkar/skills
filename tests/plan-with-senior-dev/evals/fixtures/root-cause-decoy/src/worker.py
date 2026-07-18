from .config import retry_limit


def run_job(raw_retry_limit: str | None) -> int:
    return retry_limit(raw_retry_limit)
