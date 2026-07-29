from pathlib import Path


def test_billing_modules_are_present() -> None:
    assert len(list(Path('src/billing').glob('*.py'))) >= 40
