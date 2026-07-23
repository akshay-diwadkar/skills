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
from pathlib import Path
from typing import Any, Protocol

from audit_bundle import (
    AuditBundleError,
    IssueDraft,
    format_issue_body,
    issues_from_input,
    legacy_issue,
    read_json,
)


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

    candidate_paths: list[Path] = []
    for path in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if path not in candidate_paths:
            candidate_paths.append(path)
    for path in candidate_paths:
        load_env_file(path, config)
    return config


def validate_issue(raw: Any, issue_index: int) -> IssueDraft:
    """Preserve the legacy validation API for callers and tests."""
    try:
        return legacy_issue(raw, issue_index)
    except AuditBundleError as exc:
        raise ConfigError(str(exc)) from exc


def read_issue_drafts(path: Path) -> list[IssueDraft]:
    try:
        return issues_from_input(read_json(path))
    except AuditBundleError as exc:
        raise ConfigError(str(exc)) from exc


def merge_labels(default_labels: list[str], issue_labels: list[str], extra_labels: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for label in [*default_labels, *issue_labels, *extra_labels]:
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            merged.append(label)
    return merged


class GhClient:
    def list_open_issues(self, repo: str) -> list[dict[str, object]]:
        cmd = [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "title,html_url",
            "--limit",
            "1000",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            parsed = json.loads(result.stdout)
            if not isinstance(parsed, list):
                raise GhError("gh issue list returned a non-array response")
            return parsed
        except subprocess.CalledProcessError as exc:
            raise GhError(f"gh issue list failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            raise GhError("gh cli is not installed") from exc
        except json.JSONDecodeError as exc:
            raise GhError(f"failed to parse gh issue list output: {exc}") from exc

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, object]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(body)
            body_path = handle.name

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
        body = format_issue_body(issue)
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
            print("  body:")
            for line in body.splitlines():
                print(f"    {line}")
            results.append({"status": "dry-run", "title": issue.title, "body": body})
            continue

        if client is None:
            raise ConfigError("a gh client is required when --publish is used")
        created = client.create_issue(repo, issue.title, body, labels)
        url = created.get("html_url", "")
        print(f"CREATED: {issue.title} {url}".rstrip())
        results.append({"status": "created", "title": issue.title, "url": url})

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish approved audit issue drafts to GitHub using gh cli.")
    parser.add_argument("--input", required=True, help="Path to a validated audit bundle or legacy issue JSON.")
    parser.add_argument("--publish", action="store_true", help="Create GitHub issues. Default is dry-run.")
    parser.add_argument(
        "--github-repo-url",
        help="GitHub destination as https://github.com/owner/repo, git@github.com:owner/repo.git, or owner/repo.",
    )
    parser.add_argument("--label", action="append", default=[], help="Extra label to add to every issue.")
    parser.add_argument("--no-skip-duplicates", action="store_true", help="Do not skip matching open titles.")
    parser.add_argument("--env", help="Optional .env path for labels and duplicate settings.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config_env(args.env)
        repo = normalize_github_repo_target(args.github_repo_url)
        issues = read_issue_drafts(Path(args.input))
        default_labels = parse_labels(config.get("GITHUB_DEFAULT_LABELS"))
        skip_duplicates = not args.no_skip_duplicates and parse_bool(
            config.get("GITHUB_SKIP_DUPLICATES"), default=True
        )
        client: IssueClient | None = GhClient() if args.publish else None
        publish_issues(
            issues=issues,
            client=client,
            repo=repo,
            default_labels=default_labels,
            extra_labels=args.label or [],
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
