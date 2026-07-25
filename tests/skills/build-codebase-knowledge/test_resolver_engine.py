import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import resolve_task


def test_resolver_exact_symbol_match(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "auth.py").write_text("class PasswordResetHandler:\n    def reset(self):\n        pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    res = resolve_task(tmp_path, "Fix bug in PasswordResetHandler", out_dir)
    assert res["confidence"]["level"] == "high"
    assert len(res["primary_targets"]) > 0
    assert res["primary_targets"][0]["path"] == "src/auth.py"
    assert res["primary_targets"][0]["symbol"] == "PasswordResetHandler"


def test_resolver_progressive_expansion_medium_confidence(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "orders.py").write_text("class OrderProcessor:\n    pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    res = resolve_task(tmp_path, "Refactor order module", out_dir)
    assert res["confidence"]["level"] in ["medium", "high"]
    assert len(res["read_phases"]) >= 3
    assert len(res["skip_targets"]) > 0
