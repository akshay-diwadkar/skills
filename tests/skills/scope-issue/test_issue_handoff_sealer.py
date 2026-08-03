from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "scope-issue"


def test_seals_one_typed_issue_handoff(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "names.py").write_text("def normalize_name(value):\n    return value.strip()\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/widget.git"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    issue_json = tmp_path / "issue.json"
    issue_json.write_text(
        json.dumps({"repo": "acme/widget", "fetched_at": "2026-08-03T00:00:00Z", "metadata": {"content_trust": "untrusted-github-data"}, "issues": [{"number": 7, "url": "https://github.com/acme/widget/issues/7", "updated_at": "2026-08-02T00:00:00Z"}]}),
        encoding="utf-8",
    )
    metadata = {"contract_version": 1, "source": {"repo": "acme/widget", "issue_number": 7, "issue_url": "https://github.com/acme/widget/issues/7", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z"}, "checkout": {"root": str(repo.resolve()), "remote_repo": "acme/widget", "commit": commit, "dirty": False}, "status": "plan-ready", "questions": [], "blockers": [], "close_evidence": []}
    draft = tmp_path / "draft.md"
    draft.write_text(
        "# Issue Handoff: Normalize names\n\n<!-- issue-handoff-metadata -->\n```json\n"
        + json.dumps(metadata, sort_keys=True)
        + "\n```\n\n## Outcome and Scope\n- SC-1: names are normalized consistently\n\n## Issue Claims (Untrusted)\nReporter says whitespace fails.\n\n## Local Evidence Ledger\n- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: normalization is owned here\n\n## Issue-Level Decisions\n- D-1: selected: preserve stripping | because: F-1 proves ownership | rejected: change callers\n\n## Constraints and Protected Behavior\n- C-1: preserve non-empty normalization | status: preserved\n\n## Risks and Open Questions\nNone.\n\n## Plan-Change Handoff\nPlan the implementation from current source.\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    subprocess.run([sys.executable, str(SKILL / "scripts" / "seal_issue_plan.py"), "--repo-root", str(repo), "--issue-json", str(issue_json), "--draft", str(draft), "--output-dir", str(output)], check=True, capture_output=True, text=True)
    path = output / "issue-handoff.md"
    first, body = path.read_text(encoding="utf-8").split("\n", 1)
    assert first == f"<!-- issue-handoff: 1; sha256: {hashlib.sha256(body.encode()).hexdigest()} -->"
    assert {item.name for item in output.iterdir()} == {"issue-handoff.md"}
