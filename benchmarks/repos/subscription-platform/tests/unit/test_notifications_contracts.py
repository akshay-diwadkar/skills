from pathlib import Path


def test_notifications_modules_are_present() -> None:
    assert len(list(Path('src/notifications').glob('*.py'))) >= 35
