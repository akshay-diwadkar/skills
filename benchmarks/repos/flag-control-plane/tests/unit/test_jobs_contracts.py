from pathlib import Path


def test_jobs_modules_are_present() -> None:
    assert len(list(Path('src/jobs').glob('*.py'))) >= 12
