import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import resolve_task


def test_resolve_task_exact_symbol(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, out_dir)

    res = resolve_task(sample_repo, "Fix AuthService reset_password method in auth service", out_dir)

    assert res["confidence"]["level"] in ["high", "medium"]
    assert len(res["primary_targets"]) > 0

    top_candidate = res["primary_targets"][0]
    assert "src/auth/service.py" in top_candidate["path"]
    assert top_candidate["score"] > 0.0
    assert any("exact" in r or "symbol" in r or "filename" in r for r in top_candidate["reasons"])
    assert res["source_validation_required"] is True

def test_resolve_task_progressive_expansion(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, out_dir)

    res = resolve_task(sample_repo, "Add rate limiting to password reset", out_dir)
    paths = [c["path"] for c in res["primary_targets"]]
    assert any("service.py" in p for p in paths)
