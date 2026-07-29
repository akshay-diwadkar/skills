from pathlib import Path


def test_platform_modules_are_present() -> None:
    assert len(list(Path('src/platform').glob('*.py'))) >= 30
