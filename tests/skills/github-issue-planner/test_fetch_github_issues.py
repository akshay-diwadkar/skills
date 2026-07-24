#!/usr/bin/env python3
"""Unit tests for fetch_github_issues.py."""

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

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "engineering" / "github-issue-planner" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location(
    "fetch_github_issues", SCRIPTS_DIR / "fetch_github_issues.py"
)
assert SPEC is not None
fetcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = fetcher
SPEC.loader.exec_module(fetcher)

from github_common import ConfigError, normalize_github_repo_target  # noqa: E402


def issue(number=1, title="Bug", pull_request=False):
    raw = {
        "number": number,
        "title": title,
        "body": "Issue body",
        "labels": [{"name": "bug"}],
        "user": {"login": "reporter"},
        "state": "open",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "html_url": f"https://github.com/owner/repo/issues/{number}",
    }
    if pull_request:
        raw["pull_request"] = {"url": "https://api.github.com/repos/owner/repo/pulls/2"}
    return raw


def comment():
    return {
        "id": 99,
        "body": "Clarification",
        "user": {"login": "maintainer"},
        "created_at": "2026-01-03T00:00:00Z",
        "updated_at": "2026-01-04T00:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/1#issuecomment-99",
    }


class FakeClient:
    def __init__(self):
        self.requested_comments = []

    def list_open_issues(self, repo, labels, limit):
        self.repo = repo
        self.labels = labels
        self.limit = limit
        return [issue(1, "Real issue")]

    def list_comments(self, repo, issue_number):
        self.requested_comments.append((repo, issue_number))
        return [comment()]


class FetchGitHubIssuesTests(unittest.TestCase):
    def test_repo_target_normalization_accepts_supported_forms(self):
        cases = {
            "https://github.com/owner/repo": "owner/repo",
            "https://github.com/owner/repo.git": "owner/repo",
            "git@github.com:owner/repo.git": "owner/repo",
            "ssh://git@github.com/owner/repo.git": "owner/repo",
            "owner/repo": "owner/repo",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_github_repo_target(raw), expected)

    def test_repo_target_normalization_rejects_invalid_urls(self):
        for raw in ["", "https://gitlab.com/owner/repo", "https://github.com/owner/repo/issues"]:
            with self.subTest(raw=raw):
                with self.assertRaises(ConfigError):
                    normalize_github_repo_target(raw)

    def test_fetch_filters_pull_requests_and_normalizes_comments(self):
        client = FakeClient()

        result = fetcher.fetch_issues(
            client=client,
            repo="owner/repo",
            labels=["bug"],
            limit=10,
            include_comments=True,
        )

        self.assertEqual(result["repo"], "owner/repo")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["issues"][0]["number"], 1)
        self.assertEqual(result["issues"][0]["labels"], ["bug"])
        self.assertEqual(result["issues"][0]["comments"][0]["body"], "Clarification")
        self.assertEqual(client.requested_comments, [("owner/repo", 1)])
        self.assertEqual(
            result["metadata"],
            {
                "repo": "owner/repo",
                "labels": ["bug"],
                "limit": 10,
                "comments_included": True,
                "capped": False,
                "mode": "index",
                "content_trust": "untrusted-github-data",
            },
        )

    def test_limit_counts_only_real_issues_after_pull_request_filtering(self):
        client = fetcher.PlannerGitHubClient()
        payload = [issue(2, "PR item", pull_request=True), issue(1, "Real issue")]
        with mock.patch.object(client, "request", return_value=payload):
            result = client.list_open_issues("owner/repo", labels=[], limit=1)

        self.assertEqual([item["number"] for item in result], [1])

    def test_fetch_exact_issue_includes_comments_and_trust_metadata(self):
        client = mock.Mock()
        client.get_issue.return_value = issue(7, "Selected")
        client.list_comments.return_value = [comment()]

        result = fetcher.fetch_single_issue(client, "owner/repo", 7)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["issues"][0]["number"], 7)
        self.assertEqual(result["issues"][0]["comments"][0]["body"], "Clarification")
        self.assertEqual(result["metadata"]["mode"], "single")
        self.assertEqual(result["metadata"]["content_trust"], "untrusted-github-data")

    def test_exact_issue_rejects_pull_request_number(self):
        client = fetcher.PlannerGitHubClient()
        with mock.patch.object(client, "request", return_value=issue(7, pull_request=True)):
            with self.assertRaisesRegex(ConfigError, "pull request"):
                client.get_issue("owner/repo", 7)

    @mock.patch("subprocess.run")
    def test_request_retries_transient_failures(self, mock_run):
        import subprocess
        sleeps = []
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["gh"]),
            subprocess.CalledProcessError(1, ["gh"]),
            mock.Mock(stdout='{"ok": true}'),
        ]

        client = fetcher.GitHubClient(sleep=sleeps.append)
        self.assertEqual(client.request("GET", "/repos/owner/repo/issues"), {"ok": True})

        self.assertEqual(sleeps, [1.0, 1.0])
        self.assertEqual(mock_run.call_count, 3)

    def test_write_json_atomic_replaces_output_and_removes_temp_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "issues.json"
            output_path.parent.mkdir()
            output_path.write_text("old", encoding="utf-8")

            fetcher.write_json_atomic(output_path, {"ok": True})

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), {"ok": True})
            self.assertFalse((output_path.parent / ".issues.json.tmp").exists())

    def test_main_writes_json_output_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env_path = temp / ".env"
            output_path = temp / "issues.json"
            env_path.write_text("\n", encoding="utf-8")

            fake_client = FakeClient()
            stdout = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(fetcher, "PlannerGitHubClient", return_value=fake_client),
            ):
                code = fetcher.main(
                    [
                        "--env",
                        str(env_path),
                        "--github-repo-url",
                        "https://github.com/owner/repo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(code, 0)
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data["repo"], "owner/repo")
            self.assertEqual(data["count"], 1)
            self.assertFalse(data["metadata"]["capped"])
            self.assertTrue(data["metadata"]["comments_included"])
            self.assertEqual(data["metadata"]["content_trust"], "untrusted-github-data")
            self.assertEqual(data["issues"][0]["comments"][0]["author"], "maintainer")
            self.assertIn("Fetched 1 open issue", stdout.getvalue())

    def test_main_rejects_custom_api_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env_path = temp / ".env"
            env_path.write_text("GITHUB_API_URL=https://github.example.com/api/v3\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                code = fetcher.main(
                    [
                        "--env",
                        str(env_path),
                        "--github-repo-url",
                        "owner/repo",
                        "--output",
                        str(temp / "issues.json"),
                    ]
                )
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
