import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from validate_knowledge import validate_knowledge


def test_schema_and_semantic_validation_clean(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "core.py").write_text("class Core:\n    pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    val_res = validate_knowledge(tmp_path, out_dir)
    assert val_res["status"] == "valid-fresh"
    assert len(val_res["errors"]) == 0
