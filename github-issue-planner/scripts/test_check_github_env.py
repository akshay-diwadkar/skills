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


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location("check_github_env", SCRIPTS_DIR / "check_github_env.py")
SKILL_PATH = SCRIPTS_DIR.parent / "SKILL.md"
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)

from github_common import ConfigError, normalize_github_repo_target  # noqa: E402


class CheckGitHubEnvTests(unittest.TestCase):
    def test_valid_env_file_passes_and_masks_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 0)
            output = stdout.getvalue()
            self.assertIn("Environment is ready", output)
            self.assertIn("ghp_...wxyz", output)
            self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz", output)

    def test_short_token_is_fully_masked(self):
        self.assertEqual(checker.masked("short", secret=True), "***")

    def test_long_token_is_masked_without_full_value(self):
        token = "ghp_abcdefghijklmnopqrstuvwxyz"
        masked = checker.masked(token, secret=True)
        self.assertEqual(masked, "ghp_...wxyz")
        self.assertNotIn(token, masked)

    def test_missing_token_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GITHUB_ISSUE_FETCH_LIMIT=5\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 2)

    def test_invalid_optional_config_fails_without_printing_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz\n"
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
            self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz", output)

    def test_valid_repo_url_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GITHUB_TOKEN=token\n", encoding="utf-8")
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

    def test_skill_docs_forbid_direct_env_reads(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("Never directly read `.env`", docs)
        self.assertIn("cat .env", docs)
        self.assertIn("Get-Content .env", docs)
        self.assertIn("rg ... .env", docs)
        self.assertIn("checker output must mask tokens", docs)
        self.assertIn("$skillDir\\scripts\\check_github_env.py", docs)
        self.assertIn("$skillDir\\scripts\\fetch_github_issues.py", docs)

    def test_skill_docs_preserve_opt_in_execution_boundary(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("GitHub is read-only by default", docs)
        self.assertIn("opt-in only", docs)
        self.assertIn("Use this workflow only when explicitly requested", docs)
        self.assertIn("exactly one `ready-to-plan` issue", docs)
        self.assertIn("Refs #<number>", docs)
        self.assertIn("not `Fixes #<number>`", docs)
        self.assertIn("$skillDir\\scripts\\post_merge_issue_followup.py", docs)
        self.assertIn("Do not close the issue", docs)


if __name__ == "__main__":
    unittest.main()
