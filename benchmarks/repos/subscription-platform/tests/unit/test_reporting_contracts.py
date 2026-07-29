from pathlib import Path


def test_reporting_modules_are_present() -> None:
    assert len(list(Path('src/reporting').glob('*.py'))) >= 30
