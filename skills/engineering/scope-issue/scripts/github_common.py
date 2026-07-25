#!/usr/bin/env python3
"""Shared helpers for GitHub issue planner scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
SSH_REPO_PATTERN = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?)$")


class ConfigError(Exception):
    """Raised for invalid local configuration or input."""


class GitHubError(Exception):
    """Raised for GitHub API failures."""


class GitHubClient:
    """Small shared wrapper around authenticated `gh api` requests."""

    def __init__(
        self,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.max_retries = max_retries
        self.sleep = sleep

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                cmd = ["gh", "api", path, "-X", method]
                input_payload = None
                if payload is not None:
                    cmd.extend(["--input", "-"])
                    input_payload = json.dumps(payload)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    input=input_payload,
                )
                if not result.stdout.strip():
                    return None
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as exc:
                    raise GitHubError(f"GitHub API returned invalid JSON for {method} {path}") from exc
            except subprocess.CalledProcessError as exc:
                if attempt < self.max_retries:
                    self.sleep(1.0)
                    continue
                stderr = (exc.stderr or "").strip()
                raise GitHubError(
                    f"GitHub API {method} {path} failed: {exc.returncode} {stderr}"
                ) from exc
            except FileNotFoundError as exc:
                raise GitHubError("gh cli is not installed") from exc
        raise GitHubError(f"GitHub API {method} {path} failed after retries")

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


def load_config_env(env_path: str | None = None) -> tuple[dict[str, str], list[Path]]:
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


def parse_int(value: str | None, default: int | None = None) -> int | None:
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"expected integer value, got {value!r}") from exc
    if parsed <= 0:
        raise ConfigError("integer values must be greater than zero")
    return parsed


def validate_github_api_url(value: str | None, default: str = "https://api.github.com") -> str:
    """Accept the legacy GitHub.com default and reject unsupported custom hosts."""

    raw = (value or "").strip().rstrip("/")
    if not raw or raw == default:
        return default
    raise ConfigError(
        "custom GITHUB_API_URL values are unsupported; this skill targets GitHub.com via gh cli"
    )


def parse_labels(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def masked(value: str, secret: bool = False) -> str:
    if not value:
        return "missing"
    if secret:
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}...{value[-4:]}"
    return value
