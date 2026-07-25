#!/usr/bin/env python3
"""Fetch open non-PR GitHub issues and comments into normalized JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_common import (
    ConfigError,
    GitHubClient,
    GitHubError,
    load_config_env,
    normalize_github_repo_target,
    parse_int,
    parse_labels,
    validate_github_api_url,
)


class PlannerGitHubClient(GitHubClient):
    def list_open_issues(self, repo: str, labels: list[str], limit: int | None) -> list[dict[str, Any]]:
        import urllib.parse

        encoded_repo = urllib.parse.quote(repo, safe="/")
        query = "state=open&sort=created&direction=asc"
        if labels:
            query += "&labels=" + urllib.parse.quote(",".join(labels), safe=",")
        path = f"/repos/{encoded_repo}/issues?{query}"
        issues: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self.request("GET", f"{path}&per_page=100&page={page}")
            if not isinstance(batch, list):
                raise GitHubError(f"GitHub API returned unexpected response for {path}")
            for issue in batch:
                if "pull_request" in issue:
                    continue
                issues.append(issue)
                if limit is not None and len(issues) >= limit:
                    return issues
            if len(batch) < 100:
                return issues
            page += 1

    def list_comments(self, repo: str, issue_number: int) -> list[dict[str, Any]]:
        import urllib.parse
        encoded_repo = urllib.parse.quote(repo, safe="/")
        return self.paginated_get(f"/repos/{encoded_repo}/issues/{issue_number}/comments")

    def get_issue(self, repo: str, issue_number: int) -> dict[str, Any]:
        import urllib.parse

        encoded_repo = urllib.parse.quote(repo, safe="/")
        result = self.request("GET", f"/repos/{encoded_repo}/issues/{issue_number}")
        if not isinstance(result, dict):
            raise GitHubError(f"GitHub API returned unexpected issue payload for #{issue_number}")
        if "pull_request" in result:
            raise ConfigError(f"#{issue_number} is a pull request, not an issue")
        return result


def normalize_user(raw: dict[str, Any] | None) -> str | None:
    if not raw:
        return None
    login = raw.get("login")
    return str(login) if login else None


def normalize_labels(raw_labels: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for label in raw_labels:
        name = label.get("name")
        if name:
            labels.append(str(name))
    return labels


def normalize_comment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "author": normalize_user(raw.get("user")),
        "body": raw.get("body") or "",
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "url": raw.get("html_url"),
    }


def normalize_issue(raw: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "number": raw.get("number"),
        "title": raw.get("title") or "",
        "body": raw.get("body") or "",
        "labels": normalize_labels(raw.get("labels") or []),
        "author": normalize_user(raw.get("user")),
        "state": raw.get("state"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "url": raw.get("html_url"),
        "comments": [normalize_comment(comment) for comment in comments],
    }


def fetch_issues(
    client: PlannerGitHubClient,
    repo: str,
    labels: list[str],
    limit: int | None,
    include_comments: bool = True,
) -> dict[str, Any]:
    raw_issues = client.list_open_issues(repo, labels=labels, limit=limit)
    issues = []
    for raw_issue in raw_issues:
        number = raw_issue.get("number")
        comments: list[dict[str, Any]] = []
        if include_comments and isinstance(number, int):
            comments = client.list_comments(repo, number)
        issues.append(normalize_issue(raw_issue, comments))

    return {
        "repo": repo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(issues),
        "metadata": {
            "repo": repo,
            "labels": labels,
            "limit": limit,
            "comments_included": include_comments,
            "capped": limit is not None and len(raw_issues) >= limit,
            "mode": "index",
            "content_trust": "untrusted-github-data",
        },
        "issues": issues,
    }


def fetch_single_issue(
    client: PlannerGitHubClient,
    repo: str,
    issue_number: int,
    include_comments: bool = True,
) -> dict[str, Any]:
    raw_issue = client.get_issue(repo, issue_number)
    comments = client.list_comments(repo, issue_number) if include_comments else []
    normalized = normalize_issue(raw_issue, comments)
    return {
        "repo": repo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": 1,
        "metadata": {
            "repo": repo,
            "labels": [],
            "limit": None,
            "comments_included": include_comments,
            "capped": False,
            "mode": "single",
            "content_trust": "untrusted-github-data",
        },
        "issues": [normalized],
    }


def write_json_atomic(output_path: Path, data: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch open non-PR GitHub issues and comments.")
    parser.add_argument("--env", help="Path to a .env file. Defaults to ./.env then the skill .env.")
    parser.add_argument("--github-repo-url", required=True, help="GitHub repository URL or owner/repo.")
    parser.add_argument("--output", required=True, help="Path to write normalized issue JSON.")
    parser.add_argument("--label", action="append", default=[], help="Filter open issues by label.")
    parser.add_argument("--limit", type=int, help="Maximum number of issues to fetch.")
    parser.add_argument("--issue-number", type=int, help="Fetch exactly one issue and its comments.")
    parser.add_argument("--no-comments", action="store_true", help="Fetch issue bodies without comments.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config, _ = load_config_env(args.env)

        repo = normalize_github_repo_target(args.github_repo_url)
        labels = args.label or parse_labels(config.get("GITHUB_ISSUE_FETCH_LABELS"))
        limit = args.limit if args.limit is not None else parse_int(config.get("GITHUB_ISSUE_FETCH_LIMIT"))
        validate_github_api_url(config.get("GITHUB_API_URL"))
        if args.issue_number is not None and (args.label or args.limit is not None):
            raise ConfigError("--issue-number cannot be combined with --label or --limit")
        if args.issue_number is not None and args.issue_number <= 0:
            raise ConfigError("--issue-number must be greater than zero")

        client = PlannerGitHubClient()
        if args.issue_number is not None:
            result = fetch_single_issue(
                client=client,
                repo=repo,
                issue_number=args.issue_number,
                include_comments=not args.no_comments,
            )
        else:
            result = fetch_issues(
                client=client,
                repo=repo,
                labels=labels,
                limit=limit,
                include_comments=not args.no_comments,
            )

        output_path = Path(args.output)
        write_json_atomic(output_path, result)
        noun = "issue" if result["count"] == 1 else "issues"
        print(f"Fetched {result['count']} open {noun} from {repo}")
        print(f"Wrote {output_path.resolve()}")
        return 0
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except GitHubError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
