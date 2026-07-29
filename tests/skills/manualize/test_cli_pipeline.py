from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "technical-communication" / "manualize" / "scripts"


def run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_semantic_and_finalizer_cli_contracts(
    manual_case: tuple[Path, Path, Path, dict[str, Any]],
) -> None:
    repo, manual, bundle_path, _bundle = manual_case
    checked = run("check_manual.py", "--repo-root", str(repo), "--bundle", str(bundle_path), str(manual))
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout) == {"semantic_valid": True, "errors": []}

    finalized = run("finalize_manual.py", "--repo-root", str(repo), "--bundle", str(bundle_path), str(manual))
    assert finalized.returncode == 0, finalized.stdout + finalized.stderr
    output = json.loads(finalized.stdout)
    assert output["status"] == "final"
    assert output["receipt"] == "validated"
    assert output["manual_hash"].startswith("sha256:")
    assert json.loads(bundle_path.read_text(encoding="utf-8"))["validation_receipt"]["receipt"] == "validated"


def test_audit_cli_pipeline_is_read_only(
    manual_case: tuple[Path, Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    repo, manual, bundle_path, bundle = manual_case
    bundle["operation"] = "audit"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    glossary = tmp_path / "glossary.json"
    glossary.write_text(json.dumps(bundle["glossary"]), encoding="utf-8")
    inputs = [manual, bundle_path, repo / "source.txt"]
    before = {path: (path.read_bytes(), os.stat(path).st_mtime_ns) for path in inputs}

    language = run(
        "check_manual_language.py",
        "--profile",
        bundle["profile"],
        "--glossary",
        str(glossary),
        str(manual),
    )
    semantic = run("check_manual.py", "--repo-root", str(repo), "--bundle", str(bundle_path), str(manual))
    assert language.returncode == 0, language.stdout + language.stderr
    assert semantic.returncode == 0, semantic.stdout + semantic.stderr
    assert {path: (path.read_bytes(), os.stat(path).st_mtime_ns) for path in inputs} == before

    rejected = run("finalize_manual.py", "--repo-root", str(repo), "--bundle", str(bundle_path), str(manual))
    assert rejected.returncode == 1
    assert {path: (path.read_bytes(), os.stat(path).st_mtime_ns) for path in inputs} == before
