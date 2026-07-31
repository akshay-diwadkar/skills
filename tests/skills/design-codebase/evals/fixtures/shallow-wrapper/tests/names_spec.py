from src.names import canonical_name


def test_canonical_name() -> None:
    assert canonical_name(" Ada ") == "ada"
