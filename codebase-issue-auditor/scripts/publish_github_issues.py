#!/usr/bin/env python3
"""Publish approved codebase audit issue drafts to GitHub."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}
ALLOWED_CATEGORIES = {
    "bug",
    "security",
    "performance",
    "test-gap",
    "architecture",
    "maintainability",
    "developer-experience",
}
REQUIRED_FIELDS = {
    "title",
    "body",
    "labels",
    "severity",
    "category",
    "evidence",
    "acceptance_criteria",
}
OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
SSH_REPO_PATTERN = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?)$")


class ConfigError(Exception):
    """Raised for invalid local configuration or input."""


class GitHubError(Exception):
    """Raised for GitHub API failures."""


@dataclass(frozen=True)
class IssueDraft:
    title: str
    body: str
    labels: list[str]
    severity: str
    category: str
    evidence: list[str]
    acceptance_criteria: list[str]


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_labels(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def normalize_github_repo_target(value: str | None) -> str:
    if not value or not value.strip():
        raise ConfigError("pass --github-repo-url with a GitHub URL or owner/repo target")

    target = value.strip()
    ssh_match = SSH_REPO_PATTERN.match(target)
    if ssh_match:
        target = ssh_match.group(1)
    elif OWNER_REPO_PATTERN.match(target):
        pass
    else:
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com":
            raise ConfigError(
                "--github-repo-url must be a GitHub HTTPS URL, SSH URL, or owner/repo target"
            )
        path = parsed.path.strip("/")
        if parsed.scheme == "ssh" and parsed.username and parsed.username != "git":
            raise ConfigError("SSH GitHub URLs must use the git user")
        if not OWNER_REPO_PATTERN.match(path):
            raise ConfigError("--github-repo-url must point to exactly one GitHub repository")
        target = path

    if target.endswith(".git"):
        target = target[:-4]
    if not OWNER_REPO_PATTERN.match(target):
        raise ConfigError("--github-repo-url must normalize to owner/repo")
    return target


def load_env_file(path: Path, target: dict[str, str]) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in target:
            target[key] = value


def load_config_env(env_path: str | None = None) -> dict[str, str]:
    config = dict(os.environ)
    if env_path:
        load_env_file(Path(env_path), config)
        return config

    candidate_paths = []
    for path in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if path not in candidate_paths:
            candidate_paths.append(path)
    for path in candidate_paths:
        load_env_file(path, config)
    return config


def normalize_string_list(value: Any, field: str, issue_index: int) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"issue {issue_index}: `{field}` must be a non-empty list of strings")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(f"issue {issue_index}: `{field}` must contain only non-empty strings")
        normalized.append(item.strip())
    return normalized


def validate_issue(raw: Any, issue_index: int) -> IssueDraft:
    if not isinstance(raw, dict):
        raise ConfigError(f"issue {issue_index}: expected an object")

    missing = sorted(REQUIRED_FIELDS - set(raw))
    if missing:
        raise ConfigError(f"issue {issue_index}: missing required field(s): {', '.join(missing)}")

    title = raw["title"]
    body = raw["body"]
    severity = raw["severity"]
    category = raw["category"]

    if not isinstance(title, str) or not title.strip():
        raise ConfigError(f"issue {issue_index}: `title` must be a non-empty string")
    if not isinstance(body, str) or not body.strip():
        raise ConfigError(f"issue {issue_index}: `body` must be a non-empty string")
    if severity not in ALLOWED_SEVERITIES:
        raise ConfigError(
            f"issue {issue_index}: `severity` must be one of {', '.join(sorted(ALLOWED_SEVERITIES))}"
        )
    if category not in ALLOWED_CATEGORIES:
        raise ConfigError(
            f"issue {issue_index}: `category` must be one of {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    return IssueDraft(
        title=title.strip(),
        body=body.strip(),
        labels=normalize_string_list(raw["labels"], "labels", issue_index),
        severity=severity,
        category=category,
        evidence=normalize_string_list(raw["evidence"], "evidence", issue_index),
        acceptance_criteria=normalize_string_list(
            raw["acceptance_criteria"], "acceptance_criteria", issue_index
        ),
    )


def read_issue_drafts(path: Path) -> list[IssueDraft]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc

    if isinstance(raw, dict) and "issues" in raw:
        raw_issues = raw["issues"]
    else:
        raw_issues = raw

    if not isinstance(raw_issues, list) or not raw_issues:
        raise ConfigError("input must be a non-empty issue array or an object with an `issues` array")

    return [validate_issue(issue, index + 1) for index, issue in enumerate(raw_issues)]


def merge_labels(default_labels: list[str], issue_labels: list[str], extra_labels: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for label in [*default_labels, *issue_labels, *extra_labels]:
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            merged.append(label)
    return merged


def format_issue_body(issue: IssueDraft) -> str:
    body = issue.body.strip()
    body_lower = body.lower()
    sections = [body]

    if "## evidence" not in body_lower:
        sections.append("## Evidence\n\n" + "\n".join(f"- {item}" for item in issue.evidence))
    if "## acceptance criteria" not in body_lower:
        sections.append(
            "## Acceptance criteria\n\n"
            + "\n".join(f"- [ ] {item}" for item in issue.acceptance_criteria)
        )
    if "## audit metadata" not in body_lower:
        sections.append(
            "## Audit metadata\n\n"
            f"- Severity: `{issue.severity}`\n"
            f"- Category: `{issue.category}`"
        )

    return "\n\n".join(sections)


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "codebase-issue-auditor",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self.api_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"GitHub API {method} {path} failed: {exc}") from exc

    def list_open_issues(self, repo: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        page = 1
        encoded_repo = urllib.parse.quote(repo, safe="/")
        while True:
            batch = self.request(
                "GET", f"/repos/{encoded_repo}/issues?state=open&per_page=100&page={page}"
            )
            if not isinstance(batch, list):
                raise GitHubError("GitHub open issue listing returned an unexpected response")
            issues.extend(batch)
            if len(batch) < 100:
                return issues
            page += 1

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        created = self.request(
            "POST",
            f"/repos/{encoded_repo}/issues",
            {"title": title, "body": body, "labels": labels},
        )
        if not isinstance(created, dict):
            raise GitHubError("GitHub issue creation returned an unexpected response")
        return created


def issue_exists(open_issues: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    target = title.casefold()
    for issue in open_issues:
        if str(issue.get("title", "")).casefold() == target:
            return issue
    return None


def publish_issues(
    issues: list[IssueDraft],
    client: GitHubClient | Any | None,
    repo: str,
    default_labels: list[str],
    extra_labels: list[str],
    publish: bool,
    skip_duplicates: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    open_issues: list[dict[str, Any]] = []
    if publish:
        if client is None:
            raise ConfigError("a GitHub client is required when --publish is used")
        if skip_duplicates:
            open_issues = client.list_open_issues(repo)

    for issue in issues:
        labels = merge_labels(default_labels, issue.labels, extra_labels)
        duplicate = issue_exists(open_issues, issue.title) if skip_duplicates else None
        if duplicate:
            url = duplicate.get("html_url", "")
            print(f"SKIP duplicate: {issue.title} {url}".rstrip())
            results.append({"status": "skipped", "title": issue.title, "url": url})
            continue

        if not publish:
            print(f"DRY RUN create: {issue.title}")
            print(f"  repo: {repo}")
            print(f"  labels: {', '.join(labels) if labels else '(none)'}")
            results.append({"status": "dry-run", "title": issue.title})
            continue

        created = client.create_issue(repo, issue.title, format_issue_body(issue), labels)
        url = created.get("html_url", "")
        print(f"CREATED: {issue.title} {url}".rstrip())
        results.append({"status": "created", "title": issue.title, "url": url})

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish approved audit issue drafts to GitHub.")
    parser.add_argument("--input", required=True, help="Path to issue draft JSON.")
    parser.add_argument("--publish", action="store_true", help="Create GitHub issues. Default is dry-run.")
    parser.add_argument(
        "--github-repo-url",
        help="GitHub issue destination as https://github.com/owner/repo, git@github.com:owner/repo.git, or owner/repo.",
    )
    parser.add_argument("--label", action="append", default=[], help="Extra label to add to every issue.")
    parser.add_argument("--no-skip-duplicates", action="store_true", help="Do not skip matching open titles.")
    parser.add_argument("--env", help="Optional path to a .env file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config_env(args.env)
        repo = normalize_github_repo_target(args.github_repo_url)

        issues = read_issue_drafts(Path(args.input))
        default_labels = parse_labels(config.get("GITHUB_DEFAULT_LABELS"))
        extra_labels = args.label or []
        skip_duplicates = not args.no_skip_duplicates and parse_bool(
            config.get("GITHUB_SKIP_DUPLICATES"), default=True
        )

        client = None
        if args.publish:
            token = config.get("GITHUB_TOKEN", "")
            if not token:
                raise ConfigError("set GITHUB_TOKEN before using --publish")
            client = GitHubClient(token, config.get("GITHUB_API_URL", "https://api.github.com"))

        publish_issues(
            issues=issues,
            client=client,
            repo=repo,
            default_labels=default_labels,
            extra_labels=extra_labels,
            publish=args.publish,
            skip_duplicates=skip_duplicates,
        )
        return 0
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except GitHubError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
