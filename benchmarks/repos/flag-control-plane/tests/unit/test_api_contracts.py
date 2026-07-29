from pathlib import Path


def test_api_modules_are_present() -> None:
    assert len(list(Path('src/api').glob('*.py'))) >= 16
