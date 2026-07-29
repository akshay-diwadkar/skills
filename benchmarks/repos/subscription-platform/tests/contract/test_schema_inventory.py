from pathlib import Path


def test_contract_schemas_are_committed() -> None:
    assert list(Path('schemas').glob('*.json'))
