from src.parser import parse_value


def test_parses_integer() -> None:
    assert parse_value("4") == 4
