from pathlib import Path


def test_rollouts_modules_are_present() -> None:
    assert len(list(Path('src/rollouts').glob('*.py'))) >= 20
