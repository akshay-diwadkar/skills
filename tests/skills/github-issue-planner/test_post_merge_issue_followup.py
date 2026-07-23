#!/usr/bin/env python3
"""Unit tests for post_merge_issue_followup.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "skills" / "engineering" / "github-issue-planner" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location(
    "post_merge_issue_followup", SCRIPTS_DIR / "post_merge_issue_followup.py"
)
assert SPEC is not None
followup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = followup
SPEC.loader.exec_module(followup)

from github_common import ConfigError  # noqa: E402


def pr(
    *,
    merged=True,
    base="main",
    title="Issue #7: Fix bug",
    body="Refs #7",
    number=12,
):
    return {
        "number": number,
        "title": title,
        "body": body,
        "merged": merged,
        "base": {"ref": base},
        "html_url": f"https://github.com/owner/repo/pull/{number}",
    }


def issue(*, pull_request=False):
    raw = {
        "number": 7,
        "title": "Bug",
        "body": "Broken behavior",
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/7",
    }
    if pull_request:
        raw["pull_request"] = {"url": "https://api.github.com/repos/owner/repo/pulls/7"}
    return raw


def approval():
    return {"state": "APPROVED", "user": {"login": "reviewer"}}


class FakeClient:
    def __init__(
        self,
        *,
        pr_payload=None,
        issue_payload=None,
        reviews=None,
        comments=None,
    ):
        self.pr_payload = pr_payload if pr_payload is not None else pr()
        self.issue_payload = issue_payload if issue_payload is not None else issue()
        self.reviews = reviews if reviews is not None else [approval()]
        self.comments = comments if comments is not None else []
        self.posted_comments = []

    def get_pull_request(self, repo, pr_number):
        self.repo = repo
        self.pr_number = pr_number
        return self.pr_payload

    def list_reviews(self, repo, pr_number):
        return self.reviews

    def get_issue(self, repo, issue_number):
        self.issue_number = issue_number
        return self.issue_payload

    def list_issue_comments(self, repo, issue_number):
        return self.comments

    def add_issue_comment(self, repo, issue_number, body):
        self.posted_comments.append(body)
        return {"id": 123, "body": body}


class PostMergeIssueFollowupTests(unittest.TestCase):
    def test_refuses_unmerged_pr(self):
        client = FakeClient(pr_payload=pr(merged=False))

        with self.assertRaisesRegex(ConfigError, "not merged"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertEqual(client.posted_comments, [])

    def test_refuses_wrong_base_branch(self):
        client = FakeClient(pr_payload=pr(base="develop"))

        with self.assertRaisesRegex(ConfigError, "expected main"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertEqual(client.posted_comments, [])

    def test_refuses_pr_without_approval_evidence(self):
        client = FakeClient(reviews=[{"state": "COMMENTED"}])

        with self.assertRaisesRegex(ConfigError, "no approval"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertEqual(client.posted_comments, [])

    def test_refuses_pr_that_does_not_reference_requested_issue(self):
        client = FakeClient(pr_payload=pr(title="Issue #8: Fix bug", body="Refs #8"))

        with self.assertRaisesRegex(ConfigError, "does not reference issue #7"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertEqual(client.posted_comments, [])

    def test_refuses_issue_number_that_is_a_pull_request(self):
        client = FakeClient(issue_payload=issue(pull_request=True))

        with self.assertRaisesRegex(ConfigError, "not an issue"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertEqual(client.posted_comments, [])

    def test_skips_duplicate_post_merge_comment(self):
        client = FakeClient(
            comments=[
                {
                    "id": 1,
                    "body": "<!-- github-issue-planner:issue=7:pr=12 -->\nVerified already.",
                }
            ]
        )

        message = followup.run_followup(client, "owner/repo", 7, 12, "main", "Tests pass")

        self.assertIn("already has a post-merge comment", message)
        self.assertEqual(client.posted_comments, [])

    def test_posts_expected_comment_body_with_verification_evidence(self):
        client = FakeClient()

        message = followup.run_followup(
            client,
            "owner/repo",
            7,
            12,
            "main",
            "- `python -m unittest`: pass",
        )

        self.assertIn("Commented on issue #7", message)
        self.assertEqual(len(client.posted_comments), 1)
        body = client.posted_comments[0]
        self.assertIn("github-issue-planner:issue=7:pr=12", body)
        self.assertIn("https://github.com/owner/repo/pull/12", body)
        self.assertIn("- `python -m unittest`: pass", body)

    def test_refuses_empty_verification_summary(self):
        client = FakeClient()

        with self.assertRaisesRegex(ConfigError, "verification evidence"):
            followup.run_followup(client, "owner/repo", 7, 12, "main", "  ")

        self.assertEqual(client.posted_comments, [])


if __name__ == "__main__":
    unittest.main()
