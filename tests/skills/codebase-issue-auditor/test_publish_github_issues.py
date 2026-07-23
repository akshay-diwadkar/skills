#!/usr/bin/env python3
"""Unit tests for publish_github_issues.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SCRIPT_PATH = REPO_ROOT / "skills" / "engineering" / "codebase-issue-auditor" / "scripts" / "publish_github_issues.py"
VALID_BUNDLE_PATH = DEV_DIR / "fixtures" / "valid_bundle.json"
if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("publish_github_issues", SCRIPT_PATH)
assert SPEC is not None
publisher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = publisher
SPEC.loader.exec_module(publisher)


def valid_issue() -> dict[str, object]:
    return {
        "title": "Fix missing auth check",
        "body": "The handler accepts unauthenticated requests.",
        "labels": ["audit", "security"],
        "severity": "high",
        "category": "security",
        "evidence": ["src/api.py:42 does not check the current user"],
        "acceptance_criteria": ["Unauthenticated requests return 401"],
    }


class FakeClient:
    def __init__(self, open_issues=None, create_error=None):
        self.open_issues = open_issues or []
        self.create_error = create_error
        self.created = []

    def list_open_issues(self, repo):
        return self.open_issues

    def create_issue(self, repo, title, body, labels):
        if self.create_error:
            raise self.create_error
        issue = {"html_url": f"https://github.com/{repo}/issues/{len(self.created) + 1}"}
        self.created.append((repo, title, body, labels))
        return issue


class PublishGitHubIssuesTests(unittest.TestCase):
    def write_json(self, directory: Path, payload) -> Path:
        path = directory / "issues.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_dry_run_does_not_require_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            issue_file = self.write_json(temp, [valid_issue()])
            env_file = temp / ".env"
            env_file.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output), mock.patch.dict(os.environ, {}, clear=True):
                code = publisher.main(
                    [
                        "--input",
                        str(issue_file),
                        "--env",
                        str(env_file),
                        "--github-repo-url",
                        "https://github.com/owner/repo",
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn("DRY RUN create: Fix missing auth check", output.getvalue())
            self.assertIn("repo: owner/repo", output.getvalue())
            self.assertIn("body:", output.getvalue())
            self.assertIn("## Acceptance criteria", output.getvalue())

    def test_valid_bundle_dry_run_renders_structured_body(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.dict(os.environ, {}, clear=True):
            code = publisher.main(
                [
                    "--input",
                    str(VALID_BUNDLE_PATH),
                    "--github-repo-url",
                    "owner/repo",
                ]
            )

        self.assertEqual(code, 0)
        rendered = output.getvalue()
        self.assertIn("DRY RUN create: Preserve an explicit zero retry count", rendered)
        self.assertIn("## Verification", rendered)
        self.assertIn("Candidate: `C-001`", rendered)

    def test_dry_run_requires_github_repo_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            issue_file = self.write_json(temp, [valid_issue()])
            env_file = temp / ".env"
            env_file.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = publisher.main(["--input", str(issue_file), "--env", str(env_file)])

            self.assertEqual(code, 2)

    def test_publish_reports_missing_gh_cli(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            issue_file = self.write_json(temp, [valid_issue()])
            env_file = temp / ".env"
            env_file.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr), mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "subprocess.run",
                side_effect=FileNotFoundError(),
            ):
                code = publisher.main(
                    [
                        "--input",
                        str(issue_file),
                        "--env",
                        str(env_file),
                        "--github-repo-url",
                        "owner/repo",
                        "--publish",
                    ]
                )

            self.assertEqual(code, 1)
            self.assertIn("ERROR: gh cli is not installed", stderr.getvalue())

    def test_invalid_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            issue_file = self.write_json(temp, [{"title": "Incomplete"}])
            env_file = temp / ".env"
            env_file.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = publisher.main(
                    [
                        "--input",
                        str(issue_file),
                        "--env",
                        str(env_file),
                        "--github-repo-url",
                        "owner/repo",
                    ]
                )

            self.assertEqual(code, 2)

    def test_repo_target_normalization_accepts_supported_forms(self):
        cases = {
            "https://github.com/owner/repo": "owner/repo",
            "https://github.com/owner/repo.git": "owner/repo",
            "git@github.com:owner/repo.git": "owner/repo",
            "owner/repo": "owner/repo",
            "ssh://git@github.com/owner/repo.git": "owner/repo",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(publisher.normalize_github_repo_target(raw), expected)

    def test_repo_target_normalization_rejects_invalid_urls(self):
        for raw in ["", "https://gitlab.com/owner/repo", "https://github.com/owner/repo/issues"]:
            with self.subTest(raw=raw):
                with self.assertRaises(publisher.ConfigError):
                    publisher.normalize_github_repo_target(raw)

    def test_duplicate_open_issue_is_skipped(self):
        issue = publisher.validate_issue(valid_issue(), 1)
        client = FakeClient(
            open_issues=[
                {
                    "title": "Fix missing auth check",
                    "html_url": "https://github.com/owner/repo/issues/10",
                }
            ]
        )

        results = publisher.publish_issues(
            issues=[issue],
            client=client,
            repo="owner/repo",
            default_labels=["audit"],
            extra_labels=[],
            publish=True,
            skip_duplicates=True,
        )

        self.assertEqual(results[0]["status"], "skipped")
        self.assertEqual(client.created, [])

    def test_github_api_error_is_reported(self):
        issue = publisher.validate_issue(valid_issue(), 1)
        client = FakeClient(create_error=publisher.GhError("simulated failure"))

        with self.assertRaises(publisher.GhError):
            publisher.publish_issues(
                issues=[issue],
                client=client,
                repo="owner/repo",
                default_labels=["audit"],
                extra_labels=[],
                publish=True,
                skip_duplicates=False,
            )


if __name__ == "__main__":
    unittest.main()
