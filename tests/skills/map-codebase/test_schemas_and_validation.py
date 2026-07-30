import json
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
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


def test_v6_artifacts_include_symbol_evidence_and_resolved_calls(tmp_path: Path):
    src_dir = tmp_path / "src" / "notifications"
    src_dir.mkdir(parents=True)
    (src_dir / "sender_service.py").write_text(
        "def send_digest(user_id: str) -> bool:\n    return bool(user_id)\n",
        encoding="utf-8",
    )
    (src_dir / "digest_job.py").write_text(
        "from .sender_service import send_digest\n"
        "@scheduled\n"
        "def run_digest(user_id: str):\n"
        "    return send_digest(user_id)\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / ".agent" / "knowledge"

    build_knowledge(tmp_path, out_dir)

    repo = json.loads((out_dir / "repo-map.json").read_text(encoding="utf-8"))
    relationships = json.loads((out_dir / "relationships.json").read_text(encoding="utf-8"))
    catalog = json.loads((out_dir / "symbols.json").read_text(encoding="utf-8"))
    shard = json.loads((out_dir / catalog["shards"][0]["path"]).read_text(encoding="utf-8"))
    digest = next(symbol for symbol in shard["symbols"] if symbol["name"] == "run_digest")
    digest_file = next(item for item in repo["files"] if item["path"].endswith("digest_job.py"))

    assert repo["schema_version"] == "6.0"
    assert digest_file["normalized_subsystem_path"] == "notifications"
    assert digest_file["component_types"] == ["job"]
    assert digest["signature"] == "def run_digest(user_id: str)"
    assert digest["type_hints"] == ["str"]
    assert digest["decorators"] == ["scheduled"]
    assert digest["calls"] == ["send_digest"]
    assert relationships["calls"] == [
        {
            "source": "src/notifications/digest_job.py",
            "target": "src/notifications/sender_service.py",
            "kind": "call",
            "confidence": "medium",
            "evidence": ["send_digest"],
        }
    ]
