from src.backoff import BackoffPolicy


def test_retry_schedule() -> None:
    assert BackoffPolicy().schedule_retry() == 1
