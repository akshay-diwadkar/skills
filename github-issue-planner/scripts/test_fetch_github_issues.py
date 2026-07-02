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


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location(
    "fetch_github_issues", SCRIPTS_DIR / "fetch_github_issues.py"
)
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
        return [issue(1, "Real issue"), issue(2, "PR item", pull_request=True)]

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

    def test_main_missing_token_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env_path = temp / ".env"
            output_path = temp / "issues.json"
            env_path.write_text("", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = fetcher.main(
                    [
                        "--env",
                        str(env_path),
                        "--github-repo-url",
                        "owner/repo",
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(code, 2)
            self.assertFalse(output_path.exists())

    def test_main_writes_json_output_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env_path = temp / ".env"
            output_path = temp / "issues.json"
            env_path.write_text("GITHUB_TOKEN=token\n", encoding="utf-8")

            fake_client = FakeClient()
            stdout = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(fetcher, "GitHubClient", return_value=fake_client),
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
            self.assertEqual(data["issues"][0]["comments"][0]["author"], "maintainer")
            self.assertIn("Fetched 1 open issues", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
