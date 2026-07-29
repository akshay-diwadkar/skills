from pathlib import Path


def test_catalog_modules_are_present() -> None:
    assert len(list(Path('src/catalog').glob('*.py'))) >= 35
