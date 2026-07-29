from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "engineering" / "map-codebase"
SCRIPTS = SKILL_DIR / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_knowledge as builder
from build_knowledge import EXTRACTOR_VERSION, SCHEMA_VERSION, build_knowledge
from knowledge.extraction.csharp import extract_csharp_file
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import _exact_symbol_paths, _signals, _target_tokens, compact_result, resolve_task
from validate_knowledge import validate_knowledge


def _write_owner(repo: Path, name: str = "authenticate") -> Path:
    source = repo / "src" / "auth.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f"def {name}():\n    return True\n", encoding="utf-8")
    return source


def test_resolve_is_read_only_unless_analytics_is_explicit(tmp_path: Path) -> None:
    _write_owner(tmp_path)
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    before = {path.relative_to(out): path.read_bytes() for path in out.rglob("*") if path.is_file()}

    resolve_task(tmp_path, "change authenticate", out)

    after = {path.relative_to(out): path.read_bytes() for path in out.rglob("*") if path.is_file()}
    assert after == before
    assert not (out / "analytics.jsonl").exists()

    resolve_task(tmp_path, "change authenticate", out, record_analytics=True)
    event = json.loads((out / "analytics.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert event["event"] == "resolve"
    assert event["targets_returned"] == 1


def test_symbol_index_is_exact_refreshed_and_required(tmp_path: Path) -> None:
    source = _write_owner(tmp_path)
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    original = json.loads((out / "symbol-index.json").read_text(encoding="utf-8"))
    assert _exact_symbol_paths(original, _signals("change authenticate")) == {"src/auth.py"}

    source.write_text("def authorize():\n    return True\n", encoding="utf-8")
    refresh_knowledge(tmp_path, changed_files=[str(source)], knowledge_dir=out)
    refreshed = json.loads((out / "symbol-index.json").read_text(encoding="utf-8"))
    assert "authorize" in refreshed["symbols"]
    assert "authenticate" not in refreshed["symbols"]
    assert validate_knowledge(tmp_path, out)["status"] == "valid-fresh"

    source.unlink()
    refresh_knowledge(tmp_path, changed_files=[str(source)], knowledge_dir=out)
    deleted = json.loads((out / "symbol-index.json").read_text(encoding="utf-8"))
    assert "authorize" not in deleted["symbols"]

    (out / "symbol-index.json").unlink()
    assert check_freshness(tmp_path, out)["status"] == "missing"
    assert validate_knowledge(tmp_path, out)["status"] == "invalid"


def test_symbol_index_corruption_is_rejected(tmp_path: Path) -> None:
    _write_owner(tmp_path)
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    payload = json.loads((out / "symbol-index.json").read_text(encoding="utf-8"))
    payload["symbols"].pop("authenticate")
    (out / "symbol-index.json").write_text(json.dumps(payload), encoding="utf-8")

    assert check_freshness(tmp_path, out)["status"] == "invalid"
    assert "Symbol index does not match" in " ".join(validate_knowledge(tmp_path, out)["errors"])


def test_versions_force_old_knowledge_to_rebuild(tmp_path: Path) -> None:
    _write_owner(tmp_path)
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert SCHEMA_VERSION == "5.0"
    assert EXTRACTOR_VERSION == "5.0.0"
    manifest["extractor_version"] = "4.1.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert check_freshness(tmp_path, out)["status"] == "stale"
    assert check_freshness(tmp_path, out)["staleness_detail"]["recommendation"] == "rebuild"


def test_unexpected_extractor_failures_are_not_silenced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_owner(tmp_path)

    def fail(*_args, **_kwargs):
        raise RuntimeError("parser dependency failed")

    monkeypatch.setattr(builder, "classify_and_extract", fail)
    with pytest.raises(RuntimeError, match="parser dependency failed"):
        builder.build_knowledge(tmp_path)


def test_budget_preserves_owner_evidence_and_counts_ranges(tmp_path: Path) -> None:
    _write_owner(tmp_path)
    test_source = tmp_path / "tests" / "test_auth.py"
    test_source.parent.mkdir()
    test_source.write_text(
        "from src.auth import authenticate\n\ndef test_authenticate():\n    assert authenticate()\n",
        encoding="utf-8",
    )
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    unlimited = resolve_task(tmp_path, "change authenticate", out)
    target_tokens = _target_tokens(tmp_path, unlimited["targets"][0])

    excluded = resolve_task(tmp_path, "change authenticate", out, budget=max(target_tokens - 1, 1))
    assert excluded["targets"] == []
    assert excluded["confidence"]["score"] > 0
    assert "no indexed owner matched" not in " ".join(excluded["confidence"]["reasons"])
    assert excluded["budget_detail"]["excluded_targets"][0]["path"] == "src/auth.py"

    included = resolve_task(tmp_path, "change authenticate", out, budget=target_tokens)
    assert included["targets"][0]["path"] == "src/auth.py"
    assert included["budget_detail"]["used"] == target_tokens
    assert compact_result(included)["budget_detail"] == included["budget_detail"]

    all_phases = resolve_task(tmp_path, "change authenticate", out, phase="all", budget=target_tokens)
    assert all_phases["phases"][0]["targets"][0]["path"] == "src/auth.py"
    assert all_phases["phases"][1]["targets"] == []
    assert any(item["phase"] == 2 for item in all_phases["budget_detail"]["excluded_targets"])


def test_csharp_extraction_and_dependency_are_built_in(tmp_path: Path) -> None:
    source = "using System;\nnamespace App { class Service { bool Run() { return true; } } }\n"
    path = tmp_path / "Service.cs"
    path.write_text(source, encoding="utf-8")
    symbols, imports, confidence, unknowns = extract_csharp_file(path, "Service.cs", source, "root")

    assert {"App", "Service", "Run"} <= {symbol.name for symbol in symbols}
    assert "System" in imports
    assert confidence == "high"
    assert unknowns == []
    assert "tree-sitter-c-sharp" in (SKILL_DIR / "requirements.txt").read_text(encoding="utf-8")


def test_cli_metadata_dry_run_and_opt_in_analytics(tmp_path: Path) -> None:
    _write_owner(tmp_path)
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    cli = SCRIPTS / "cli.py"

    status = subprocess.run(
        [sys.executable, str(cli), "status", "--repo-root", str(tmp_path), "--output", str(out), "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(status.stdout)["_meta"]["command"] == "status"

    dry_repo = tmp_path / "dry"
    dry_repo.mkdir()
    _write_owner(dry_repo)
    generated = dry_repo / "generated" / "client.py"
    generated.parent.mkdir()
    generated.write_text("def generated_client(): pass\n", encoding="utf-8")
    dry_run = subprocess.run(
        [sys.executable, str(cli), "build", "--repo-root", str(dry_repo), "--dry-run", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    dry_payload = json.loads(dry_run.stdout)
    assert dry_payload["_meta"] == {"command": "build", "dry_run": True}
    assert dry_payload["files_excluded"] >= 1
    assert not (dry_repo / ".agent" / "knowledge").exists()

    subprocess.run(
        [
            sys.executable,
            str(cli),
            "resolve",
            "change authenticate",
            "--repo-root",
            str(tmp_path),
            "--output",
            str(out),
            "--record-analytics",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert (out / "analytics.jsonl").is_file()
