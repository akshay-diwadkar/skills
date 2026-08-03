from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "raise-issue" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import publish_github_issues as publisher  # noqa: E402


def sealed_handoff(*, issue: bool = True) -> str:
    body = "\n".join(
        [
            "# Audit Issue Handoff",
            "",
            "## Audit Context",
            "",
            '- Target: "/repo"',
            '- Commit: "abc123"',
            "- Dirty worktree: false",
            "- Limitations: []",
            f"- Issue count: {1 if issue else 0}",
            *(
                [
                    "",
                    "## Issue C-001",
                    "",
                    '- Title: "Preserve zero retries"',
                    '- Labels: ["audit","bug"]',
                    '- Severity: "medium"',
                    '- Category: "bug"',
                    '- Confidence: "high"',
                    '- Affected workflow: "job submission"',
                    "",
                    "### Summary",
                    "",
                    "Zero retries are replaced.",
                    "",
                    "### Impact",
                    "",
                    "A job repeats side effects.",
                    "",
                    "### Root Cause",
                    "",
                    "Truthiness fallback.",
                    "",
                    "### Evidence",
                    "",
                    "- app/jobs.py:18: zero selects the default",
                    "",
                    "### Verification",
                    "",
                    "- Add a regression test.",
                    "",
                    "### Acceptance Criteria",
                    "",
                    "- [ ] Preserve zero.",
                ]
                if issue
                else ["", "## Issues", "", "No accepted findings."]
            ),
        ]
    ) + "\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    return f"<!-- audit-handoff: 1; sha256: {digest} -->\n{body}"


class FakeClient:
    def __init__(
        self,
        *,
        open_issues=None,
        failures=None,
        auth_error: Exception | None = None,
        list_error: Exception | None = None,
    ):
        self.open_issues = open_issues or []
        self.failures = failures or {}
        self.auth_error = auth_error
        self.list_error = list_error
        self.created: list[str] = []

    def authenticate(self) -> None:
        if self.auth_error:
            raise self.auth_error

    def list_open_issues(self, repo: str):
        if self.list_error:
            raise self.list_error
        return self.open_issues

    def create_issue(self, repo: str, issue: publisher.Issue) -> str:
        self.created.append(issue.title)
        if issue.title in self.failures:
            raise publisher.PublicationError(self.failures[issue.title])
        return f"https://github.com/{repo}/issues/{len(self.created)}"


def test_preview_verifies_receipt_target_and_labels(tmp_path: Path) -> None:
    handoff = tmp_path / "audit-handoff.md"
    handoff.write_text(sealed_handoff(), encoding="utf-8")
    payload = publisher.preview_payload(handoff, "https://github.com/owner/repo.git", ["Audit", "extra"])
    assert payload["github_repo"] == "owner/repo"
    assert payload["issues"][0]["labels"] == ["audit", "bug", "extra"]
    handoff.write_text(handoff.read_text(encoding="utf-8") + "tampered", encoding="utf-8")
    with pytest.raises(publisher.PublicationError, match="receipt does not match"):
        publisher.preview_payload(handoff, "owner/repo", [])


@pytest.mark.parametrize(
    "raw",
    [
        "owner/repo",
        "https://github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
        "ssh://git@github.com/owner/repo.git",
    ],
)
def test_target_normalization_accepts_supported_forms(raw: str) -> None:
    assert publisher.normalize_github_repo_target(raw) == "owner/repo"


@pytest.mark.parametrize(
    "raw",
    ["", "https://gitlab.com/owner/repo", "https://github.com/owner/repo/issues"],
)
def test_target_normalization_rejects_ambiguous_forms(raw: str) -> None:
    with pytest.raises(publisher.PublicationError):
        publisher.normalize_github_repo_target(raw)


def test_publish_skips_duplicates_and_reports_partial() -> None:
    preview = {
        "schema_version": 1,
        "handoff_sha256": "hash",
        "github_repo": "owner/repo",
        "issues": [
            {"candidate_id": "C-1", "title": "Duplicate", "body": "body", "labels": ["audit"]},
            {"candidate_id": "C-2", "title": "Fails", "body": "body", "labels": ["audit"]},
            {"candidate_id": "C-3", "title": "Created", "body": "body", "labels": ["audit"]},
        ],
    }
    client = FakeClient(
        open_issues=[{"title": "duplicate", "html_url": "https://example/1"}],
        failures={"Fails": "ambiguous failure"},
    )
    result = publisher.publish(preview, client)
    assert result["overall_status"] == "partial"
    assert [item["status"] for item in result["items"]] == ["duplicate", "failed", "created"]
    assert client.created == ["Fails", "Created"]


def test_global_failure_creates_nothing() -> None:
    preview = {
        "schema_version": 1,
        "handoff_sha256": "hash",
        "github_repo": "owner/repo",
        "issues": [{"candidate_id": "C-1", "title": "Issue", "body": "body", "labels": ["audit"]}],
    }
    client = FakeClient(auth_error=publisher.PublicationError("not authenticated"))
    with pytest.raises(publisher.PublicationError):
        publisher.publish(preview, client)
    assert client.created == []


def test_duplicate_listing_failure_creates_nothing() -> None:
    preview = {
        "schema_version": 1,
        "handoff_sha256": "hash",
        "github_repo": "owner/repo",
        "issues": [{"candidate_id": "C-1", "title": "Issue", "body": "body", "labels": ["audit"]}],
    }
    client = FakeClient(list_error=publisher.PublicationError("listing failed"))
    with pytest.raises(publisher.PublicationError):
        publisher.publish(preview, client)
    assert client.created == []


def test_publish_rejects_preview_drift_before_github(tmp_path: Path) -> None:
    handoff = tmp_path / "audit-handoff.md"
    preview = tmp_path / "preview.json"
    output = tmp_path / "result.json"
    handoff.write_text(sealed_handoff(issue=False), encoding="utf-8")
    payload = publisher.preview_payload(handoff, "owner/repo", [])
    payload["github_repo"] = "other/repo"
    publisher.write_json(preview, payload)
    client = FakeClient()

    code = publisher.main(
        [
            "publish",
            "--handoff",
            str(handoff),
            "--github-repo-url",
            "owner/repo",
            "--preview",
            str(preview),
            "--publish-confirmation",
            "yes",
            "--output",
            str(output),
        ],
        client=client,
    )

    assert code == 1
    assert client.created == []
    assert not output.exists()


def test_publish_cli_requires_explicit_confirmation(tmp_path: Path) -> None:
    handoff = tmp_path / "audit-handoff.md"
    preview = tmp_path / "preview.json"
    output = tmp_path / "result.json"
    handoff.write_text(sealed_handoff(issue=False), encoding="utf-8")
    publisher.write_json(preview, publisher.preview_payload(handoff, "owner/repo", []))

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "publish_github_issues.py"),
            "publish",
            "--handoff",
            str(handoff),
            "--github-repo-url",
            "owner/repo",
            "--preview",
            str(preview),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--publish-confirmation" in result.stderr
    assert not output.exists()


def test_protocol_requires_late_confirmation_and_zero_issue_needs_no_gh(tmp_path: Path) -> None:
    handoff = tmp_path / "audit-handoff.md"
    handoff.write_text(sealed_handoff(issue=False), encoding="utf-8")
    run_dir = tmp_path / "run"
    cli = ROOT / "skills" / "engineering" / "raise-issue" / "scripts" / "cli.py"
    start = subprocess.run(
        [sys.executable, str(cli), "--repo-root", str(ROOT), "--run-dir", str(run_dir), "--input", f"handoff={handoff}", "--input", "github_repo_url=owner/repo", "--format", "json", "start"],
        capture_output=True,
        text=True,
    )
    assert start.returncode == 0, start.stderr or start.stdout
    assert json.loads(start.stdout)["phase"] == "approval-required"
    publish = subprocess.run(
        [sys.executable, str(cli), "--repo-root", str(ROOT), "--run-dir", str(run_dir), "--input", "publish_confirmation=yes", "--format", "json", "next"],
        capture_output=True,
        text=True,
    )
    assert publish.returncode == 0, publish.stderr or publish.stdout
    assert json.loads(publish.stdout)["phase"] == "complete"
    assert json.loads((run_dir / "publication-result.json").read_text())["overall_status"] == "no-op"
