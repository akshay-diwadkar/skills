#!/usr/bin/env python3
"""Unit tests for check_github_env.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "github-issue-planner"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location("check_github_env", SCRIPTS_DIR / "check_github_env.py")
SKILL_PATH = SKILL_ROOT / "SKILL.md"
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)

from github_common import ConfigError, normalize_github_repo_target  # noqa: E402


class CheckGitHubEnvTests(unittest.TestCase):
    @mock.patch("subprocess.run")
    def test_valid_env_file_passes(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 0)
            output = stdout.getvalue()
            self.assertIn("Environment is ready", output)
            self.assertIn("gh cli: authenticated", output)

    def test_short_token_is_fully_masked(self):
        self.assertEqual(checker.masked("short", secret=True), "***")

    def test_long_token_is_masked_without_full_value(self):
        token = "ghp_abcdefghijklmnopqrstuvwxyz"
        masked = checker.masked(token, secret=True)
        self.assertEqual(masked, "ghp_...wxyz")
        self.assertNotIn(token, masked)

    @mock.patch("subprocess.run")
    def test_missing_gh_cli_auth_fails(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, ["gh", "auth", "status"])
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GITHUB_ISSUE_FETCH_LIMIT=5\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 2)

    @mock.patch("subprocess.run")
    def test_invalid_optional_config_fails(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GITHUB_ISSUE_FETCH_LIMIT=zero\n"
                "GITHUB_API_URL=not-a-url\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 2)
            output = stdout.getvalue()
            self.assertIn("GITHUB_ISSUE_FETCH_LIMIT: invalid", output)
            self.assertIn("GITHUB_API_URL: invalid", output)

    @mock.patch("subprocess.run")
    def test_valid_repo_url_passes(self, mock_run):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(
                    [
                        "--env",
                        str(env_path),
                        "--github-repo-url",
                        "git@github.com:owner/repo.git",
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn("GitHub issue source: owner/repo", stdout.getvalue())

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

    def test_skill_docs_mention_scripts(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("$skillDir\\scripts\\check_github_env.py", docs)
        self.assertIn("$skillDir\\scripts\\fetch_github_issues.py", docs)

    def test_skill_docs_preserve_opt_in_execution_boundary(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("Planning is GitHub-read-only", docs)
        self.assertIn("opt-in only", docs)
        self.assertIn("after explicit user authorization", docs)
        self.assertIn("one issue per branch", docs)
        self.assertIn("Never batch issues into one branch or PR", docs)
        self.assertIn("Refs #<number>", docs)
        self.assertIn("never an auto-close keyword", docs)
        self.assertIn("$skillDir\\scripts\\post_merge_issue_followup.py", docs)
        self.assertIn("never closes or labels", docs)

    def test_skill_docs_require_validated_single_issue_handoff(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("plan one issue per pass", docs.lower())
        self.assertIn("Issue Claims (Untrusted)", docs)
        self.assertIn("ready-for-senior-plan", docs)
        self.assertIn("$plan-with-senior-dev", docs)
        self.assertIn("check_issue_plan.py", docs)


if __name__ == "__main__":
    unittest.main()
