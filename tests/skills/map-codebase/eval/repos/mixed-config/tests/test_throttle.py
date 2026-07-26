from app.throttle import ThrottlePolicy


def test_rate_limit() -> None:
    assert ThrottlePolicy().allow_request()
