from pathlib import Path


def test_evaluation_modules_are_present() -> None:
    assert len(list(Path('src/evaluation').glob('*.py'))) >= 20
