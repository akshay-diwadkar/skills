import json
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge


def test_build_knowledge_artifacts(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    assert not (sample_repo / "AGENTS.md").exists()
    assert not (sample_repo / "CLAUDE.md").exists()
    assert not (sample_repo / ".github" / "workflows" / "refresh-codebase-knowledge.yml").exists()
    res = build_knowledge(sample_repo, out_dir)

    assert res["status"] == "success"
    assert not (out_dir / "index.json").exists()
    assert (out_dir / "repo-map.json").is_file()
    assert (out_dir / "symbols.json").is_file()
    assert (out_dir / "relationships.json").is_file()
    assert not (out_dir / "context.md").exists()
    assert not (out_dir / "architecture.md").exists()
    assert (out_dir / "manifest.json").is_file()
    assert not (sample_repo / "AGENTS.md").exists()
    assert not (sample_repo / "CLAUDE.md").exists()
    assert not (sample_repo / ".github" / "workflows" / "refresh-codebase-knowledge.yml").exists()

    index_data = json.loads((out_dir / "repo-map.json").read_text(encoding="utf-8"))
    assert index_data["schema_version"] == "4.0"
    assert len(index_data["files"]) > 0

    # Verify vendor code is excluded
    indexed_paths = [f["path"] for f in index_data["files"]]
    assert not any("vendor" in p for p in indexed_paths)
