from names import normalize_name


def test_normalizes_name() -> None:
    assert normalize_name(" Ada ") == "Ada"
    assert normalize_name("") == ""
