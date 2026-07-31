from src.exporter import export_csv


def test_exports_csv() -> None:
    assert export_csv([{"name": "Ada"}]) == "name\r\nAda\r\n"
