from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "scope-issue"
FIXTURES = ROOT / "tests" / "skills" / "scope-issue" / "fixtures"

SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("check_issue_handoff_sealer_import", SCRIPTS / "check_issue_plan.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    source = (FIXTURES / "repo" / "src" / "names.py").read_text(encoding="utf-8")
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "names.py").write_text(source, encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/widget.git"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    return repo, commit


def json_escape_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\")


def seal(repo: Path, fixture: Path, tmp_path: Path) -> Path:
    scope_inputs = fixture / "scope-inputs.json"
    snapshot = fixture / "snapshot.json"
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    draft = fixture / "draft.md"
    draft_text = draft.read_text(encoding="utf-8").replace("{{ROOT}}", json_escape_path(repo)).replace("{{COMMIT}}", commit)
    draft_path = tmp_path / "draft.md"
    draft_path.write_text(draft_text, encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_issue_plan.py"), "--repo-root", str(repo), "--issue-json", str(snapshot), "--scope-inputs", str(scope_inputs), "--draft", str(draft_path), "--output-dir", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    return output / "issue-handoff.md"


def test_seals_one_typed_plan_ready_handoff(tmp_path: Path) -> None:
    repo, _commit = init_repo(tmp_path)
    path = seal(repo, FIXTURES / "v2" / "plan-ready-one-child", tmp_path)
    first, body = path.read_text(encoding="utf-8").split("\n", 1)
    assert first == f"<!-- issue-handoff: 1; sha256: {hashlib.sha256(body.encode()).hexdigest()} -->"
    assert {item.name for item in path.parent.iterdir()} == {"issue-handoff.md"}


def test_seals_single_issue_compatibility_handoff(tmp_path: Path) -> None:
    repo, _commit = init_repo(tmp_path)
    path = seal(repo, FIXTURES / "v2" / "single-issue-compat", tmp_path)
    first, body = path.read_text(encoding="utf-8").split("\n", 1)
    assert first == f"<!-- issue-handoff: 1; sha256: {hashlib.sha256(body.encode()).hexdigest()} -->"
    assert "## Selection Stage" in body
    assert '"contract_version":2' in body


def test_equivalent_drafts_canonicalize_byte_identically(tmp_path: Path) -> None:
    repo, commit = init_repo(tmp_path)
    fixture = FIXTURES / "v2" / "plan-ready-one-child"
    base = fixture / "draft.md"
    base_text = base.read_text(encoding="utf-8").replace("{{ROOT}}", json_escape_path(repo)).replace("{{COMMIT}}", commit)

    output_a = tmp_path / "out-a"
    output_a.mkdir()
    draft_a = tmp_path / "a.md"
    with open(draft_a, "w", encoding="utf-8", newline="") as draft_handle:
        draft_handle.write(base_text.replace("\n", "\r\n"))
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_issue_plan.py"), "--repo-root", str(repo), "--issue-json", str(fixture / "snapshot.json"), "--scope-inputs", str(fixture / "scope-inputs.json"), "--draft", str(draft_a), "--output-dir", str(output_a)],
        check=True,
        capture_output=True,
        text=True,
    )

    metadata_match = MODULE.METADATA_RE.search(base_text)
    assert metadata_match is not None
    metadata = json.loads(metadata_match.group("json"))
    reordered = {key: metadata[key] for key in reversed(list(metadata))}
    shuffled = base_text[: metadata_match.start("json")] + json.dumps(reordered) + base_text[metadata_match.end("json"):]
    output_b = tmp_path / "out-b"
    output_b.mkdir()
    draft_b = tmp_path / "b.md"
    with open(draft_b, "w", encoding="utf-8", newline="") as draft_handle:
        draft_handle.write(shuffled)
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_issue_plan.py"), "--repo-root", str(repo), "--issue-json", str(fixture / "snapshot.json"), "--scope-inputs", str(fixture / "scope-inputs.json"), "--draft", str(draft_b), "--output-dir", str(output_b)],
        check=True,
        capture_output=True,
        text=True,
    )

    sealed_a = (output_a / "issue-handoff.md").read_bytes()
    sealed_b = (output_b / "issue-handoff.md").read_bytes()
    assert sealed_a == sealed_b
