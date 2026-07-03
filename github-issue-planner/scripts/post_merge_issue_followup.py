#!/usr/bin/env python3
"""Post a verified post-merge issue comment for a resolved issue PR."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from github_common import (
    ConfigError,
    GitHubError,
    load_config_env,
    normalize_github_repo_target,
    validate_github_api_url,
)


MARKER_TEMPLATE = "github-issue-planner:issue={issue_number}:pr={pr_number}"


class GitHubClient:
    def __init__(
        self,
        token: str,
        api_url: str = "https://api.github.com",
        max_retries: int = 3,
        sleep=time.sleep,
    ) -> None:
        self.token = token
        self.api_url = validate_github_api_url(api_url)
        self.max_retries = max_retries
        self.sleep = sleep

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "github-issue-planner",
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
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    text = response.read().decode("utf-8")
                    return json.loads(text) if text else None
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if self._should_retry_http(exc) and attempt < self.max_retries:
                    self.sleep(self._retry_delay(exc))
                    continue
                raise GitHubError(
                    f"GitHub API {method} {path} failed: {exc.code} {detail}"
                ) from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries:
                    self.sleep(1.0)
                    continue
                raise GitHubError(f"GitHub API {method} {path} failed: {exc}") from exc
        raise GitHubError(f"GitHub API {method} {path} failed after retries")

    def _should_retry_http(self, exc: urllib.error.HTTPError) -> bool:
        if exc.code == 429 or exc.code >= 500:
            return True
        remaining = exc.headers.get("X-RateLimit-Remaining")
        return exc.code == 403 and remaining == "0"

    def _retry_delay(self, exc: urllib.error.HTTPError) -> float:
        retry_after = exc.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), 60.0)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    return min(max(retry_at.timestamp() - time.time(), 0.0), 60.0)
                except (TypeError, ValueError):
                    pass

        reset_at = exc.headers.get("X-RateLimit-Reset")
        if reset_at:
            try:
                return min(max(float(reset_at) - time.time(), 0.0), 60.0)
            except ValueError:
                pass

        return 1.0

    def paginated_get(self, path: str) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            batch = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise GitHubError(f"GitHub API returned unexpected response for {path}")
            collected.extend(batch)
            if len(batch) < 100:
                return collected
            page += 1

    def get_pull_request(self, repo: str, pr_number: int) -> dict[str, Any]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        result = self.request("GET", f"/repos/{encoded_repo}/pulls/{pr_number}")
        if not isinstance(result, dict):
            raise GitHubError(f"GitHub API returned unexpected PR payload for #{pr_number}")
        return result

    def list_reviews(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        return self.paginated_get(f"/repos/{encoded_repo}/pulls/{pr_number}/reviews")

    def get_issue(self, repo: str, issue_number: int) -> dict[str, Any]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        result = self.request("GET", f"/repos/{encoded_repo}/issues/{issue_number}")
        if not isinstance(result, dict):
            raise GitHubError(f"GitHub API returned unexpected issue payload for #{issue_number}")
        return result

    def list_issue_comments(self, repo: str, issue_number: int) -> list[dict[str, Any]]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        return self.paginated_get(f"/repos/{encoded_repo}/issues/{issue_number}/comments")

    def add_issue_comment(self, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        encoded_repo = urllib.parse.quote(repo, safe="/")
        result = self.request(
            "POST",
            f"/repos/{encoded_repo}/issues/{issue_number}/comments",
            {"body": body},
        )
        if not isinstance(result, dict):
            raise GitHubError(f"GitHub API returned unexpected comment payload for #{issue_number}")
        return result


def marker(issue_number: int, pr_number: int) -> str:
    return MARKER_TEMPLATE.format(issue_number=issue_number, pr_number=pr_number)


def pr_references_issue(pr: dict[str, Any], issue_number: int) -> bool:
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")
    issue_ref = re.compile(rf"(?<!\d)#{re.escape(str(issue_number))}(?!\d)")
    return bool(
        issue_ref.search(title)
        or issue_ref.search(body)
        or f"/issues/{issue_number}" in body
    )


def has_approval(reviews: list[dict[str, Any]]) -> bool:
    return any(str(review.get("state") or "").upper() == "APPROVED" for review in reviews)


def validate_followup_inputs(
    pr: dict[str, Any],
    issue: dict[str, Any],
    reviews: list[dict[str, Any]],
    issue_number: int,
    base: str,
) -> None:
    if not pr.get("merged"):
        raise ConfigError(f"PR #{pr.get('number', 'unknown')} is not merged")

    actual_base = ((pr.get("base") or {}).get("ref") or "").strip()
    if actual_base != base:
        raise ConfigError(f"PR targets {actual_base or 'unknown'}, expected {base}")

    if not has_approval(reviews):
        raise ConfigError("PR has no approval review")

    if "pull_request" in issue:
        raise ConfigError(f"#{issue_number} is a pull request, not an issue")

    if not pr_references_issue(pr, issue_number):
        raise ConfigError(f"PR does not reference issue #{issue_number}")


def build_comment(
    repo: str,
    issue_number: int,
    pr_number: int,
    pr: dict[str, Any],
    verification_summary: str,
) -> str:
    pr_url = pr.get("html_url") or f"https://github.com/{repo}/pull/{pr_number}"
    marker_text = marker(issue_number, pr_number)
    return (
        f"<!-- {marker_text} -->\n"
        f"Verified on `main` after merge: {pr_url}\n\n"
        "Resolution evidence:\n\n"
        f"{verification_summary.strip()}\n"
    )


def already_commented(comments: list[dict[str, Any]], issue_number: int, pr_number: int) -> bool:
    marker_text = marker(issue_number, pr_number)
    return any(marker_text in str(comment.get("body") or "") for comment in comments)


def run_followup(
    client: GitHubClient,
    repo: str,
    issue_number: int,
    pr_number: int,
    base: str,
    verification_summary: str,
) -> str:
    if not verification_summary.strip():
        raise ConfigError("--verification-summary-file must contain verification evidence")

    pr = client.get_pull_request(repo, pr_number)
    reviews = client.list_reviews(repo, pr_number)
    issue = client.get_issue(repo, issue_number)
    validate_followup_inputs(pr, issue, reviews, issue_number, base)

    comments = client.list_issue_comments(repo, issue_number)
    if already_commented(comments, issue_number, pr_number):
        return f"Issue #{issue_number} already has a post-merge comment for PR #{pr_number}."

    body = build_comment(repo, issue_number, pr_number, pr, verification_summary)
    client.add_issue_comment(repo, issue_number, body)
    return f"Commented on issue #{issue_number} with merged PR #{pr_number} verification."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Comment on an issue after its PR is merged and verified.")
    parser.add_argument("--env", help="Path to a .env file. Defaults to ./.env then the skill .env.")
    parser.add_argument("--github-repo-url", required=True, help="GitHub repository URL or owner/repo.")
    parser.add_argument("--issue-number", required=True, type=int, help="Resolved GitHub issue number.")
    parser.add_argument("--pr-number", required=True, type=int, help="Merged GitHub pull request number.")
    parser.add_argument("--base", default="main", help="Expected merged PR base branch. Defaults to main.")
    parser.add_argument(
        "--verification-summary-file",
        required=True,
        help="Markdown file containing the verification evidence from updated main.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config, _ = load_config_env(args.env)
        token = config.get("GITHUB_TOKEN", "")
        if not token:
            raise ConfigError("set GITHUB_TOKEN before posting post-merge issue comments")

        repo = normalize_github_repo_target(args.github_repo_url)
        api_url = validate_github_api_url(config.get("GITHUB_API_URL"))
        summary_path = Path(args.verification_summary_file)
        verification_summary = summary_path.read_text(encoding="utf-8")

        client = GitHubClient(token, api_url)
        print(
            run_followup(
                client=client,
                repo=repo,
                issue_number=args.issue_number,
                pr_number=args.pr_number,
                base=args.base,
                verification_summary=verification_summary,
            )
        )
        return 0
    except FileNotFoundError as exc:
        print(f"ERROR: verification summary file not found: {exc.filename}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except GitHubError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
