from src.names import normalize_name


def test_strips_non_null_name() -> None:
    assert normalize_name(" Ada ") == "Ada"
