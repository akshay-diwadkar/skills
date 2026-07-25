import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from validate_knowledge import validate_knowledge


def test_validate_knowledge_fresh(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, out_dir)

    res = validate_knowledge(sample_repo, out_dir)
    assert res["status"] == "valid-fresh"
    assert len(res["errors"]) == 0
