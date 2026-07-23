from src.caller import display_name


def test_displays_name() -> None:
    assert display_name("Ada") == "Ada"
