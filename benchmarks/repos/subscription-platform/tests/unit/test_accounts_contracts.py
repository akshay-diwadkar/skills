from pathlib import Path


def test_accounts_modules_are_present() -> None:
    assert len(list(Path('src/accounts').glob('*.py'))) >= 35
