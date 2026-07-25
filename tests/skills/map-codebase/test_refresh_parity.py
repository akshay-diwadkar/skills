import json
import shutil
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import refresh_knowledge


def _semantic(out: Path) -> dict:
    data = {
        name: json.loads((out / name).read_text(encoding="utf-8"))
        for name in ("repo-map.json", "relationships.json", "symbols.json")
    }
    return data


def test_refresh_matches_clean_build_and_preserves_unrelated_shards(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "other").mkdir()
    (repo / "src" / "service.py").write_text("class Old:\n    pass\n", encoding="utf-8")
    (repo / "other" / "stable.py").write_text("class Stable:\n    pass\n", encoding="utf-8")
    out = repo / ".agent" / "knowledge"
    build_knowledge(repo, out)
    stable_before = (out / "symbols" / "other.json").read_bytes()
    (repo / "src" / "service.py").write_text("class New:\n    pass\n", encoding="utf-8")
    refresh_knowledge(repo, ["src/service.py"], out)
    incremental = _semantic(out)
    assert (out / "symbols" / "other.json").read_bytes() == stable_before
    shutil.rmtree(out)
    build_knowledge(repo, out)
    assert incremental == _semantic(out)


def test_generated_file_stays_generated_after_refresh(tmp_path: Path):
    repo = tmp_path / "repo"
    generated = repo / "src" / "generated"
    generated.mkdir(parents=True)
    target = generated / "models.py"
    target.write_text("class A:\n    pass\n", encoding="utf-8")
    out = repo / ".agent" / "knowledge"
    build_knowledge(repo, out)
    target.write_text("class B:\n    pass\n", encoding="utf-8")
    refresh_knowledge(repo, ["src/generated/models.py"], out)
    files = json.loads((out / "repo-map.json").read_text(encoding="utf-8"))["files"]
    assert next(item for item in files if item["path"] == "src/generated/models.py")["generated"]
