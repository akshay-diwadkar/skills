from pathlib import Path

def test_decode_education_western_operator_pending_has_a_component_boundary() -> None:
    source = Path("go/receivers/decode_education_western_operator_pending.go")
    content = source.read_text(encoding="utf-8")
    assert source.is_file()
    assert "tenant" in content.casefold()
    assert "contract" in "component contract"
