from src.authentication import AuthenticationService


def test_login_acceptance() -> None:
    assert AuthenticationService().authenticate_user()
