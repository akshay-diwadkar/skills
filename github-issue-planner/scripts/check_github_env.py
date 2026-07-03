#!/usr/bin/env python3
"""Check GitHub environment configuration without printing secrets."""

from __future__ import annotations

import argparse
import sys

from github_common import (
    ConfigError,
    load_config_env,
    masked,
    normalize_github_repo_target,
    parse_int,
    validate_github_api_url,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check GitHub issue planner environment.")
    parser.add_argument("--env", help="Path to a .env file. Defaults to ./.env then the skill .env.")
    parser.add_argument("--github-repo-url", help="Optional GitHub issue source URL to validate.")
    args = parser.parse_args(argv)

    config, loaded = load_config_env(args.env)
    problems: list[str] = []

    if not config.get("GITHUB_TOKEN"):
        problems.append("GITHUB_TOKEN")

    fetch_limit = "missing"
    try:
        parsed_limit = parse_int(config.get("GITHUB_ISSUE_FETCH_LIMIT"))
        if parsed_limit is not None:
            fetch_limit = str(parsed_limit)
    except ConfigError as exc:
        fetch_limit = "invalid"
        problems.append(f"GITHUB_ISSUE_FETCH_LIMIT invalid: {exc}")

    api_url = "missing"
    try:
        api_url = validate_github_api_url(config.get("GITHUB_API_URL"))
    except ConfigError as exc:
        api_url = "invalid"
        problems.append(f"GITHUB_API_URL invalid: {exc}")

    repo = "not checked"
    if args.github_repo_url:
        try:
            repo = normalize_github_repo_target(args.github_repo_url)
        except ConfigError as exc:
            repo = "invalid"
            problems.append(f"--github-repo-url invalid: {exc}")

    if loaded:
        print("Loaded env file(s):")
        for path in loaded:
            print(f"  {path}")
    else:
        print("Loaded env file(s): none")

    print("GitHub issue planner environment:")
    print(f"  GITHUB_TOKEN: {masked(config.get('GITHUB_TOKEN', ''), secret=True)}")
    print(f"  GitHub issue source: {repo}")
    print(f"  GITHUB_ISSUE_FETCH_LABELS: {masked(config.get('GITHUB_ISSUE_FETCH_LABELS', ''))}")
    print(f"  GITHUB_ISSUE_FETCH_LIMIT: {fetch_limit}")
    print(f"  GITHUB_API_URL: {api_url}")

    if problems:
        print("Missing or invalid configuration:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    print("Environment is ready for GitHub issue fetching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
