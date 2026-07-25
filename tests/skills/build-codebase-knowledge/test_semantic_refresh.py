import json
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import check_freshness, refresh_knowledge


def test_semantic_refresh_symbol_addition(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    svc_file = src_dir / "service.py"
    svc_file.write_text("class OriginalService:\n    pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    # Modify file to add a new symbol
    svc_file.write_text("class OriginalService:\n    pass\n\nclass AddedService:\n    pass\n", encoding="utf-8")

    fresh_before = check_freshness(tmp_path, out_dir)
    assert fresh_before["status"] == "partially-stale"

    # Refresh knowledge semantically
    ref_res = refresh_knowledge(tmp_path, ["src/service.py"], out_dir)
    assert ref_res["mode"] == "incremental"
    assert ref_res["status"] == "fresh"

    catalog = json.loads((out_dir / "symbols.json").read_text(encoding="utf-8"))
    indexed_symbol_names = [s["name"] for shard in catalog["shards"] for s in json.loads((out_dir / shard["path"]).read_text(encoding="utf-8"))["symbols"]]
    assert "AddedService" in indexed_symbol_names
    assert "OriginalService" in indexed_symbol_names


def test_semantic_refresh_file_deletion(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    f1 = src_dir / "m1.py"
    f2 = src_dir / "m2.py"
    f1.write_text("import m2\nclass C1: pass\n", encoding="utf-8")
    f2.write_text("class C2: pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    # Delete m2.py
    f2.unlink()

    ref_res = refresh_knowledge(tmp_path, ["src/m2.py"], out_dir)
    assert ref_res["status"] == "fresh"

    index_data = json.loads((out_dir / "repo-map.json").read_text(encoding="utf-8"))
    indexed_paths = [f["path"] for f in index_data["files"]]
    assert "src/m2.py" not in indexed_paths
