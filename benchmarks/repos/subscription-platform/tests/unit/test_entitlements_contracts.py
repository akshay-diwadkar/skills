from pathlib import Path


def test_entitlements_modules_are_present() -> None:
    assert len(list(Path('src/entitlements').glob('*.py'))) >= 30
