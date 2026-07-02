#!/usr/bin/env python3
"""Fetch open non-PR GitHub issues and comments into normalized JSON."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_common import (
    ConfigError,
    GitHubError,
    load_config_env,
    normalize_github_repo_target,
    parse_int,
    parse_labels,
)


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str) -> Any:
        request = urllib.request.Request(
            self.api_url + path,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "github-issue-planner",
                "X-GitHub-Api-Version": "2022-11-28",
            },
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

    def paginated_get(self, path: str, limit: int | None = None) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            batch = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise GitHubError(f"GitHub API returned unexpected response for {path}")
            collected.extend(batch)
            if limit is not None and len(collected) >= limit:
                return collected[:limit]
            if len(batch) < 100:
                return collected
            page += 1

    def list_open_issues(self, repo: str, labels: list[str], limit: int | None) -> list[dict[str, Any]]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        query = "state=open&sort=created&direction=asc"
        if labels:
            query += "&labels=" + urllib.parse.quote(",".join(labels), safe=",")
        issues = self.paginated_get(f"/repos/{encoded_repo}/issues?{query}", limit=limit)
        return [issue for issue in issues if "pull_request" not in issue]

    def list_comments(self, repo: str, issue_number: int) -> list[dict[str, Any]]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        return self.paginated_get(f"/repos/{encoded_repo}/issues/{issue_number}/comments")


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
    client: GitHubClient,
    repo: str,
    labels: list[str],
    limit: int | None,
    include_comments: bool = True,
) -> dict[str, Any]:
    raw_issues = [
        issue for issue in client.list_open_issues(repo, labels=labels, limit=limit)
        if "pull_request" not in issue
    ]
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
        "issues": issues,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch open non-PR GitHub issues and comments.")
    parser.add_argument("--env", help="Path to a .env file. Defaults to ./.env then the skill .env.")
    parser.add_argument("--github-repo-url", required=True, help="GitHub repository URL or owner/repo.")
    parser.add_argument("--output", required=True, help="Path to write normalized issue JSON.")
    parser.add_argument("--label", action="append", default=[], help="Filter open issues by label.")
    parser.add_argument("--limit", type=int, help="Maximum number of issues to fetch.")
    parser.add_argument("--no-comments", action="store_true", help="Fetch issue bodies without comments.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config, _ = load_config_env(args.env)
        token = config.get("GITHUB_TOKEN", "")
        if not token:
            raise ConfigError("set GITHUB_TOKEN before fetching issues")

        repo = normalize_github_repo_target(args.github_repo_url)
        labels = args.label or parse_labels(config.get("GITHUB_ISSUE_FETCH_LABELS"))
        limit = args.limit if args.limit is not None else parse_int(config.get("GITHUB_ISSUE_FETCH_LIMIT"))
        client = GitHubClient(token, config.get("GITHUB_API_URL", "https://api.github.com"))
        result = fetch_issues(
            client=client,
            repo=repo,
            labels=labels,
            limit=limit,
            include_comments=not args.no_comments,
        )

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Fetched {result['count']} open issues from {repo}")
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
