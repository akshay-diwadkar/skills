#!/usr/bin/env python3
"""Check GitHub environment configuration without printing secrets."""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path


REQUIRED_KEYS = ("GITHUB_TOKEN",)
OPTIONAL_KEYS = ("GITHUB_DEFAULT_LABELS", "GITHUB_SKIP_DUPLICATES", "GITHUB_API_URL")
OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
SSH_REPO_PATTERN = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?)$")


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


def load_config(env_path: str | None = None) -> tuple[dict[str, str], list[Path]]:
    config = dict(os.environ)
    if env_path:
        path = Path(env_path)
        load_env_file(path, config)
        return config, [path.resolve()] if path.exists() else []

    candidates: list[Path] = []
    for path in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if path not in candidates:
            candidates.append(path)

    loaded: list[Path] = []
    for path in candidates:
        if path.exists():
            load_env_file(path, config)
            loaded.append(path.resolve())
    return config, loaded


def masked(value: str, secret: bool = False) -> str:
    if not value:
        return "missing"
    if secret:
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"
    return value


def normalize_github_repo_target(value: str | None) -> str:
    if not value or not value.strip():
        raise ValueError("missing target")

    target = value.strip()
    ssh_match = SSH_REPO_PATTERN.match(target)
    if ssh_match:
        target = ssh_match.group(1)
    elif OWNER_REPO_PATTERN.match(target):
        pass
    else:
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com":
            raise ValueError("target must be a GitHub HTTPS URL, SSH URL, or owner/repo")
        path = parsed.path.strip("/")
        if parsed.scheme == "ssh" and parsed.username and parsed.username != "git":
            raise ValueError("SSH GitHub URLs must use the git user")
        if not OWNER_REPO_PATTERN.match(path):
            raise ValueError("target must point to exactly one GitHub repository")
        target = path

    if target.endswith(".git"):
        target = target[:-4]
    if not OWNER_REPO_PATTERN.match(target):
        raise ValueError("target must normalize to owner/repo")
    return target


def check(config: dict[str, str], github_repo_url: str | None = None) -> list[str]:
    missing = [key for key in REQUIRED_KEYS if not config.get(key)]
    if github_repo_url:
        try:
            normalize_github_repo_target(github_repo_url)
        except ValueError as exc:
            missing.append(f"--github-repo-url invalid: {exc}")
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check GitHub issue publishing environment.")
    parser.add_argument("--env", help="Path to a .env file. Defaults to ./.env then the skill .env.")
    parser.add_argument("--github-repo-url", help="Optional GitHub issue destination URL to validate.")
    args = parser.parse_args(argv)

    config, loaded = load_config(args.env)
    problems = check(config, args.github_repo_url)

    if loaded:
        print("Loaded env file(s):")
        for path in loaded:
            print(f"  {path}")
    else:
        print("Loaded env file(s): none")

    print("GitHub issue publishing environment:")
    print(f"  GITHUB_TOKEN: {masked(config.get('GITHUB_TOKEN', ''), secret=True)}")
    if args.github_repo_url:
        try:
            repo = normalize_github_repo_target(args.github_repo_url)
        except ValueError:
            repo = "invalid"
        print(f"  GitHub issue target: {repo}")
    else:
        print("  GitHub issue target: not checked")
    for key in OPTIONAL_KEYS:
        print(f"  {key}: {masked(config.get(key, ''))}")

    if problems:
        print("Missing or invalid configuration:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    print("Environment is ready for GitHub issue publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
