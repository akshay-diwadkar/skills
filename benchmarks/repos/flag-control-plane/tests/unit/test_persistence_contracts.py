from pathlib import Path


def test_persistence_modules_are_present() -> None:
    assert len(list(Path('src/persistence').glob('*.py'))) >= 16
