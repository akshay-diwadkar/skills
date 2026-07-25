from app.api import list_accounts, submit_job


def test_submit_job_uses_default_retries() -> None:
    assert submit_job({}) == {"attempts": 4}


def test_submit_job_accepts_positive_retries() -> None:
    assert submit_job({"retries": 2}) == {"attempts": 3}


def test_admin_can_list_accounts() -> None:
    assert list_accounts({"role": "admin"}) == ["a-1"]
