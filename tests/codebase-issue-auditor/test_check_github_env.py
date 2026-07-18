#!/usr/bin/env python3
"""Unit tests for check_github_env.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "codebase-issue-auditor" / "scripts" / "check_github_env.py"
SKILL_PATH = REPO_ROOT / "codebase-issue-auditor" / "SKILL.md"
SPEC = importlib.util.spec_from_file_location("check_github_env", SCRIPT_PATH)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class CheckGitHubEnvTests(unittest.TestCase):
    @mock.patch("subprocess.run")
    def test_valid_env_file_passes_with_gh_auth(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(["gh", "auth", "status"], 0, "", "")
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 0)
            output = stdout.getvalue()
            self.assertIn("Environment is ready", output)
            self.assertIn("gh CLI auth: OK", output)
            self.assertIn("GitHub issue target: not checked", output)

    @mock.patch("subprocess.run")
    def test_missing_gh_cli_auth_fails(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["gh", "auth", "status"],
            1,
            "",
            "not authenticated",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GITHUB_DEFAULT_LABELS=audit\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(["--env", str(env_path)])

            self.assertEqual(code, 2)

    @mock.patch("subprocess.run")
    def test_valid_env_with_repo_url_passes(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(["gh", "auth", "status"], 0, "", "")
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")

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
            self.assertIn("GitHub issue target: owner/repo", stdout.getvalue())

    @mock.patch("subprocess.run")
    def test_invalid_repo_url_fails(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(["gh", "auth", "status"], 0, "", "")
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True):
                code = checker.main(
                    [
                        "--env",
                        str(env_path),
                        "--github-repo-url",
                        "https://gitlab.com/owner/repo",
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
                self.assertEqual(checker.normalize_github_repo_target(raw), expected)

    def test_repo_target_normalization_rejects_invalid_urls(self):
        for raw in ["", "https://gitlab.com/owner/repo", "https://github.com/owner/repo/issues"]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    checker.normalize_github_repo_target(raw)

    def test_skill_docs_document_gh_cli_configuration(self):
        docs = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/check_github_env.py", docs)
        self.assertIn("python scripts/publish_github_issues.py", docs)
        self.assertIn("--publish", docs)
        self.assertIn("Never publish or close issues implicitly", docs)


if __name__ == "__main__":
    unittest.main()
