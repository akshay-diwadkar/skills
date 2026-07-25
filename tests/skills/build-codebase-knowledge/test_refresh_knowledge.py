import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import check_freshness, refresh_knowledge


def test_refresh_knowledge_incremental(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, out_dir)

    st_before = check_freshness(sample_repo, out_dir)
    assert st_before["status"] == "fresh"

    # Modify file
    target_f = sample_repo / "src" / "auth" / "service.py"
    target_f.write_text(target_f.read_text(encoding="utf-8") + "\n# added comment\n", encoding="utf-8")

    st_mod = check_freshness(sample_repo, out_dir)
    assert st_mod["status"] == "partially-stale"

    # Perform refresh
    res = refresh_knowledge(sample_repo, ["src/auth/service.py"], out_dir)
    assert res["status"] == "fresh"
    assert res["mode"] == "incremental"

    st_after = check_freshness(sample_repo, out_dir)
    assert st_after["status"] == "fresh"
