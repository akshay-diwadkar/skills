from unittest.mock import patch

from src.cli import main


@patch("src.cli.parse_document")
def test_cli_uses_parser(mock_parse):
    mock_parse.return_value = "invoice"
    assert main(" INVOICE ") == "invoice"
