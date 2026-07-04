#!/usr/bin/env python3
"""Publish approved codebase audit issue drafts to GitHub using gh cli."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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


class GhError(Exception):
    """Raised for gh cli failures."""


class IssueClient(Protocol):
    def list_open_issues(self, repo: str) -> list[dict[str, object]]:
        """Return open issue metadata for duplicate checks."""

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, object]:
        """Create one issue and return created issue metadata."""


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
        import urllib.parse
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


class GhClient:
    def list_open_issues(self, repo: str) -> list[dict[str, object]]:
        cmd = ["gh", "issue", "list", "--repo", repo, "--state", "open", "--json", "title,html_url", "--limit", "1000"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as exc:
            raise GhError(f"gh issue list failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            raise GhError("gh cli is not installed") from exc
        except json.JSONDecodeError as exc:
            raise GhError(f"Failed to parse gh issue list output: {exc}") from exc

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, object]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write(body)
            body_path = f.name

        try:
            cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_path]
            for label in labels:
                cmd.extend(["--label", label])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"html_url": result.stdout.strip()}
        except subprocess.CalledProcessError as exc:
            raise GhError(f"gh issue create failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            raise GhError("gh cli is not installed") from exc
        finally:
            if os.path.exists(body_path):
                os.remove(body_path)


def issue_exists(open_issues: list[dict[str, object]], title: str) -> dict[str, object] | None:
    target = title.casefold()
    for issue in open_issues:
        if str(issue.get("title", "")).casefold() == target:
            return issue
    return None


def publish_issues(
    issues: list[IssueDraft],
    client: IssueClient | None,
    repo: str,
    default_labels: list[str],
    extra_labels: list[str],
    publish: bool,
    skip_duplicates: bool,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    open_issues: list[dict[str, object]] = []
    if publish:
        if client is None:
            raise ConfigError("a gh client is required when --publish is used")
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

        if client is None:
            raise ConfigError("a gh client is required when --publish is used")
        created = client.create_issue(repo, issue.title, format_issue_body(issue), labels)
        url = created.get("html_url", "")
        print(f"CREATED: {issue.title} {url}".rstrip())
        results.append({"status": "created", "title": issue.title, "url": url})

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish approved audit issue drafts to GitHub using gh cli.")
    parser.add_argument("--input", required=True, help="Path to issue draft JSON.")
    parser.add_argument("--publish", action="store_true", help="Create GitHub issues. Default is dry-run.")
    parser.add_argument(
        "--github-repo-url",
        help="GitHub issue destination as https://github.com/owner/repo, git@github.com:owner/repo.git, or owner/repo.",
    )
    parser.add_argument("--label", action="append", default=[], help="Extra label to add to every issue.")
    parser.add_argument("--no-skip-duplicates", action="store_true", help="Do not skip matching open titles.")
    parser.add_argument("--env", help="Optional path to a .env file (only for labels and duplicate settings now).")
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
            client = GhClient()

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
    except GhError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
