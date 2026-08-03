#!/usr/bin/env python3
"""Preview and publish receipt-sealed audit handoffs through gh."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

RECEIPT_RE = re.compile(r"^<!-- audit-handoff: 1; sha256: ([0-9a-f]{64}) -->$")
ISSUE_RE = re.compile(r"^## Issue ([^\n]+)\n", re.MULTILINE)
CONTEXT_RE = re.compile(
    r'^# Audit Issue Handoff\n\n## Audit Context\n\n'
    r'- Target: (?P<target>.+)\n'
    r'- Commit: (?P<commit>.+)\n'
    r'- Dirty worktree: (?P<dirty>.+)\n'
    r'- Limitations: (?P<limitations>.+)\n'
    r'- Issue count: (?P<count>\d+)\n'
)
ISSUE_BLOCK_RE = re.compile(
    r'^- Title: (?P<title>.+)\n'
    r'- Labels: (?P<labels>.+)\n'
    r'- Severity: (?P<severity>.+)\n'
    r'- Category: (?P<category>.+)\n'
    r'- Confidence: (?P<confidence>.+)\n'
    r'- Affected workflow: (?P<workflow>.+)\n\n'
    r'(?P<body>### Summary\n\n.+?\n\n'
    r'### Impact\n\n.+?\n\n'
    r'### Root Cause\n\n.+?\n\n'
    r'### Evidence\n\n(?:- [^\n]+\n)+'
    r'\n### Verification\n\n(?:- [^\n]+\n)+'
    r'\n### Acceptance Criteria\n\n(?:- \[ \] [^\n]+(?:\n|$))+)$',
    re.DOTALL,
)
OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
SSH_REPO_RE = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?)$")
GH_TIMEOUT_SECONDS = 30


class PublicationError(Exception):
    """Raised when publication cannot safely start."""


@dataclass(frozen=True)
class Issue:
    candidate_id: str
    title: str
    body: str
    labels: tuple[str, ...]


class IssueClient(Protocol):
    def authenticate(self) -> None: ...
    def list_open_issues(self, repo: str) -> list[dict[str, Any]]: ...
    def create_issue(self, repo: str, issue: Issue) -> str: ...


def normalize_github_repo_target(value: str) -> str:
    """Normalize supported GitHub targets to owner/repo."""
    target = value.strip()
    ssh_match = SSH_REPO_RE.fullmatch(target)
    if ssh_match:
        target = ssh_match.group(1)
    elif not OWNER_REPO_RE.fullmatch(target):
        parsed = urllib.parse.urlparse(target)
        if (
            parsed.scheme not in {"https", "ssh"}
            or parsed.hostname != "github.com"
            or parsed.query
            or parsed.fragment
        ):
            raise PublicationError("github_repo_url must be a GitHub HTTPS URL, SSH URL, or owner/repo")
        if parsed.scheme == "ssh" and parsed.username not in {None, "git"}:
            raise PublicationError("SSH GitHub URLs must use the git user")
        target = parsed.path.strip("/")
    target = target.removesuffix(".git")
    if not OWNER_REPO_RE.fullmatch(target):
        raise PublicationError("github_repo_url must point to exactly one GitHub repository")
    return target


def _json_value(value: str, name: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise PublicationError(f"handoff issue has invalid {name}") from exc


def parse_handoff(path: Path) -> tuple[str, list[Issue]]:
    """Verify and parse one sealed handoff."""
    text = path.read_text(encoding="utf-8")
    receipt, separator, body = text.partition("\n")
    match = RECEIPT_RE.fullmatch(receipt)
    if not separator or match is None:
        raise PublicationError("handoff receipt is missing or malformed")
    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != match.group(1):
        raise PublicationError("handoff receipt does not match content")
    context_match = CONTEXT_RE.match(body)
    if context_match is None:
        raise PublicationError("handoff audit context is malformed")
    target = _json_value(context_match.group("target"), "Target")
    commit = _json_value(context_match.group("commit"), "Commit")
    dirty = _json_value(context_match.group("dirty"), "Dirty worktree")
    limitations = _json_value(context_match.group("limitations"), "Limitations")
    if not isinstance(target, str) or not target or not isinstance(commit, str) or not commit:
        raise PublicationError("handoff audit context target and commit must be non-empty strings")
    if not isinstance(dirty, bool) or not isinstance(limitations, list) or not all(
        isinstance(item, str) for item in limitations
    ):
        raise PublicationError("handoff audit context types are invalid")
    issue_region = body[context_match.end() :]
    matches = list(ISSUE_RE.finditer(issue_region))
    if int(context_match.group("count")) != len(matches):
        raise PublicationError("handoff issue count does not match issue sections")
    if not matches:
        if issue_region != "\n## Issues\n\nNo accepted findings.\n":
            raise PublicationError("zero-issue handoff state is malformed")
        return actual, []
    if matches[0].start() != 1:
        raise PublicationError("handoff contains content outside issue sections")
    issues: list[Issue] = []
    seen_titles: set[str] = set()
    for index, issue_match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(issue_region)
        block = issue_region[issue_match.end() : end].strip()
        block_match = ISSUE_BLOCK_RE.fullmatch(block)
        if block_match is None:
            raise PublicationError("handoff issue body is incomplete or malformed")
        title = _json_value(block_match.group("title"), "Title")
        labels = _json_value(block_match.group("labels"), "Labels")
        metadata_groups = {
            "Severity": "severity",
            "Category": "category",
            "Confidence": "confidence",
            "Affected workflow": "workflow",
        }
        for name, group in metadata_groups.items():
            value = _json_value(block_match.group(group), name)
            if not isinstance(value, str) or not value:
                raise PublicationError(f"handoff issue {name} must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise PublicationError("handoff issue title must be a non-empty string")
        if not isinstance(labels, list) or not labels or not all(isinstance(item, str) and item for item in labels):
            raise PublicationError("handoff issue labels must be a non-empty string array")
        title_key = title.casefold()
        if title_key in seen_titles:
            raise PublicationError("handoff issue titles must be unique ignoring case")
        seen_titles.add(title_key)
        issues.append(
            Issue(
                issue_match.group(1),
                title.strip(),
                block_match.group("body").strip(),
                tuple(labels),
            )
        )
    return actual, issues


def merge_labels(issue_labels: tuple[str, ...], extra_labels: list[str]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for label in (*issue_labels, *extra_labels):
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            merged.append(label)
    return tuple(merged)


def preview_payload(handoff: Path, repo_value: str, extra_labels: list[str]) -> dict[str, Any]:
    handoff_sha256, issues = parse_handoff(handoff)
    repo = normalize_github_repo_target(repo_value)
    return {
        "schema_version": 1,
        "handoff_sha256": handoff_sha256,
        "github_repo": repo,
        "issues": [
            {
                "candidate_id": issue.candidate_id,
                "title": issue.title,
                "body": issue.body,
                "labels": list(merge_labels(issue.labels, extra_labels)),
            }
            for issue in issues
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace one deterministic run artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            delete=False,
        ) as temp:
            temp.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            temporary_path = Path(temp.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class GhClient:
    def _run(self, argv: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                argv,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            raise PublicationError("gh cli is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise PublicationError(f"gh command timed out after {GH_TIMEOUT_SECONDS} seconds") from exc

    def authenticate(self) -> None:
        result = self._run(["gh", "auth", "status"])
        if result.returncode != 0:
            raise PublicationError(f"gh authentication failed: {result.stderr.strip()}")

    def list_open_issues(self, repo: str) -> list[dict[str, Any]]:
        result = self._run(
            ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/issues?state=open&per_page=100"]
        )
        if result.returncode != 0:
            raise PublicationError(f"open issue listing failed: {result.stderr.strip()}")
        try:
            pages = json.loads(result.stdout)
            return [item for page in pages for item in page if "pull_request" not in item]
        except (json.JSONDecodeError, TypeError) as exc:
            raise PublicationError("open issue listing returned invalid JSON") from exc

    def create_issue(self, repo: str, issue: Issue) -> str:
        argv = ["gh", "issue", "create", "--repo", repo, "--title", issue.title, "--body-file", "-"]
        for label in issue.labels:
            argv.extend(["--label", label])
        result = self._run(argv, input_text=issue.body)
        if result.returncode != 0:
            raise PublicationError(result.stderr.strip() or "gh issue create failed with ambiguous outcome")
        return result.stdout.strip()


def publish(preview: dict[str, Any], client: IssueClient) -> dict[str, Any]:
    issues = [
        Issue(item["candidate_id"], item["title"], item["body"], tuple(item["labels"]))
        for item in preview["issues"]
    ]
    if not issues:
        return {
            "schema_version": 1,
            "handoff_sha256": preview["handoff_sha256"],
            "github_repo": preview["github_repo"],
            "overall_status": "no-op",
            "items": [],
        }
    client.authenticate()
    open_issues = client.list_open_issues(preview["github_repo"])
    by_title = {str(item.get("title", "")).casefold(): item for item in open_issues}
    results: list[dict[str, Any]] = []
    for issue in issues:
        duplicate = by_title.get(issue.title.casefold())
        if duplicate is not None:
            results.append(
                {
                    "candidate_id": issue.candidate_id,
                    "title": issue.title,
                    "status": "duplicate",
                    "url": str(duplicate.get("html_url", "")),
                }
            )
            continue
        try:
            url = client.create_issue(preview["github_repo"], issue)
            results.append({"candidate_id": issue.candidate_id, "title": issue.title, "status": "created", "url": url})
        except PublicationError as exc:
            results.append(
                {
                    "candidate_id": issue.candidate_id,
                    "title": issue.title,
                    "status": "failed",
                    "error": str(exc),
                    "reconciliation": "Rerun after checking open issues; exact-title duplicate detection prevents a second create.",
                }
            )
    overall = "partial" if any(item["status"] == "failed" for item in results) else "success"
    return {
        "schema_version": 1,
        "handoff_sha256": preview["handoff_sha256"],
        "github_repo": preview["github_repo"],
        "overall_status": overall,
        "items": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preview_parser = subparsers.add_parser("preview")
    publish_parser = subparsers.add_parser("publish")
    for command_parser in (preview_parser, publish_parser):
        command_parser.add_argument("--handoff", type=Path, required=True)
        command_parser.add_argument("--github-repo-url", required=True)
        command_parser.add_argument("--label", action="append", default=[])
        command_parser.add_argument("--output", type=Path, required=True)
    publish_parser.add_argument("--preview", type=Path, required=True)
    publish_parser.add_argument("--publish-confirmation", choices=("yes",), required=True)
    return parser


def main(argv: list[str] | None = None, *, client: IssueClient | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        current_preview = preview_payload(args.handoff, args.github_repo_url, args.label)
        if args.command == "preview":
            write_json(args.output, current_preview)
            print(json.dumps({"status": "approval-required", "path": str(args.output)}, sort_keys=True))
            return 0
        stored_preview = json.loads(args.preview.read_text(encoding="utf-8"))
        if stored_preview != current_preview:
            raise PublicationError("handoff, target, labels, or preview changed after approval")
        result = publish(current_preview, client or GhClient())
        write_json(args.output, result)
        print(json.dumps({"status": "complete", "path": str(args.output)}, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, PublicationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
