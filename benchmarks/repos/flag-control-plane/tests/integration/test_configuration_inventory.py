from pathlib import Path


def test_every_service_has_configuration() -> None:
    assert list(Path('config').glob('*'))
