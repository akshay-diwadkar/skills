#!/usr/bin/env python3
"""Validate one source-bound, handoff-only GitHub issue artifact."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from github_common import ConfigError, normalize_github_repo_target

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = SKILL_ROOT / "references" / "issue-plan-contract.json"
METADATA_RE = re.compile(r"<!-- issue-handoff-metadata -->\s*```json\s*(?P<json>\{.*?\})\s*```", re.DOTALL)
RECORD_CANDIDATE_RE = re.compile(r"^\s*[-*]\s*(?P<prefix>SC|F|D|C|CH|T)-(?P<number>[^:\s]*)(?P<tail>.*)$")
RECORD_TOKENIZERS = {
    "SC": re.compile(r"^- SC-(?P<number>\d+):\s*(?P<body>.+)$"),
    "F": re.compile(r"^- F-(?P<number>\d+): `(?P<path>[^`]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<body>.+)$"),
    "D": re.compile(r"^- D-(?P<number>\d+): selected: (?P<selected>.+?) \| because: (?P<because>.+?) \| rejected: (?P<rejected>.+)$"),
    "C": re.compile(r"^- C-(?P<number>\d+): (?P<body>.+?) \| status: (?P<status>preserved|modified|at-risk)$"),
}


class HandoffContractError(ValueError):
    """Raised when trusted source material cannot be reconciled."""


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffContractError(f"unable to read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffContractError(f"{label} must contain a JSON object")
    return value


def _nested(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise HandoffContractError(f"unable to inspect git checkout: {' '.join(args)}") from exc
    return result.stdout.strip()


def parse_metadata(text: str) -> dict[str, Any]:
    match = METADATA_RE.search(text)
    if match is None:
        raise HandoffContractError("missing issue-handoff metadata JSON block")
    value = json.loads(match.group("json"))
    if not isinstance(value, dict):
        raise HandoffContractError("issue-handoff metadata must be an object")
    return value


def _trusted_text(text: str) -> str:
    start = text.find("## Issue Claims (Untrusted)")
    end = text.find("## Local Evidence Ledger", start + 1)
    if start < 0 or end < 0:
        return text
    return text[:start] + "## Issue Claims (Untrusted)\n<untrusted-content-removed>\n" + text[end:]


def _parse_records(text: str, formats: dict[str, str]) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    records: dict[str, list[dict[str, str]]] = {prefix: [] for prefix in RECORD_TOKENIZERS}
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        candidate = RECORD_CANDIDATE_RE.fullmatch(line)
        if candidate is None:
            continue
        prefix = candidate.group("prefix")
        if prefix not in RECORD_TOKENIZERS:
            errors.append(f"line {line_number}: {prefix} records belong to plan-change, not scope-issue")
            continue
        match = RECORD_TOKENIZERS[prefix].fullmatch(line)
        if match is None:
            errors.append(f"line {line_number}: expected {formats[prefix]}")
        else:
            records[prefix].append(match.groupdict())
    for prefix, items in records.items():
        numbers = [int(item["number"]) for item in items]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{prefix} records must use sequential IDs starting at 1")
    return records, errors


def _validate_facts(records: dict[str, list[dict[str, str]]], repo_root: Path, issue_json: Path) -> list[str]:
    errors: list[str] = []
    for fact in records["F"]:
        raw_path = fact["path"]
        path = (repo_root / raw_path).resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            errors.append(f"F-{fact['number']} path escapes the repository")
            continue
        if path == issue_json.resolve() or ".scratch" in path.parts or not path.is_file():
            errors.append(f"F-{fact['number']} must cite an existing repository file")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        line_number = int(fact["line"])
        if line_number < 1 or line_number > len(lines) or fact["anchor"] not in lines[line_number - 1]:
            errors.append(f"F-{fact['number']} anchor is absent from {raw_path}:{line_number}")
    return errors


def _validate_source(metadata: dict[str, Any], payload: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    source = metadata.get("source") or {}
    checkout = metadata.get("checkout") or {}
    issues = payload.get("issues")
    number = source.get("issue_number")
    matches = [item for item in issues or [] if isinstance(item, dict) and item.get("number") == number]
    if len(matches) != 1:
        return ["source.issue_number must identify exactly one fetched issue"]
    issue = matches[0]
    for field, actual, expected in (
        ("source.repo", source.get("repo"), payload.get("repo")),
        ("source.issue_url", source.get("issue_url"), issue.get("url")),
        ("source.issue_updated_at", source.get("issue_updated_at"), issue.get("updated_at")),
        ("source.fetched_at", source.get("fetched_at"), payload.get("fetched_at")),
    ):
        if actual != expected:
            errors.append(f"{field} does not match the selected issue JSON")
    actual_root = Path(_git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    try:
        remote_repo = normalize_github_repo_target(_git(actual_root, "remote", "get-url", "origin"))
    except ConfigError as exc:
        errors.append(str(exc))
        remote_repo = ""
    if Path(str(checkout.get("root") or "")).resolve() != actual_root:
        errors.append("checkout.root does not match --repo-root")
    if checkout.get("remote_repo") != remote_repo or source.get("repo") != remote_repo:
        errors.append("checkout origin does not match issue source")
    if checkout.get("commit") != _git(actual_root, "rev-parse", "HEAD"):
        errors.append("issue handoff is stale because HEAD changed")
    return errors


def validate_plan(plan_path: Path, issue_json: Path, repo_root: Path) -> list[str]:
    contract = _load_object(CONTRACT_PATH, "issue handoff contract")
    text = plan_path.read_text(encoding="utf-8")
    metadata = parse_metadata(text)
    clean = _trusted_text(text)
    errors: list[str] = []
    for field in contract["required_metadata"]:
        if _nested(metadata, field) is None:
            errors.append(f"missing metadata field {field}")
    if metadata.get("contract_version") != contract["contract_version"]:
        errors.append(f"metadata contract_version must be {contract['contract_version']}")
    status = metadata.get("status")
    if status not in contract["statuses"]:
        errors.append(f"status must be one of: {', '.join(contract['statuses'])}")
    for field in ("questions", "blockers", "close_evidence"):
        if not isinstance(metadata.get(field), list):
            errors.append(f"metadata {field} must be an array")
    errors.extend(f"missing section: {name}" for name in contract["required_sections"] if f"## {name}" not in text)
    for token in contract["placeholder_tokens"]:
        if re.search(rf"\b{re.escape(token)}\b", clean, re.IGNORECASE):
            errors.append(f"unresolved placeholder token: {token}")
    records, record_errors = _parse_records(clean, contract["record_formats"])
    errors.extend(record_errors)
    rule = contract["status_requirements"].get(status, {})
    errors.extend(f"status {status} requires at least one {prefix} record" for prefix in rule.get("records", []) if not records[prefix])
    if rule.get("questions_required") and not metadata.get("questions"):
        errors.append(f"status {status} requires questions")
    if rule.get("blockers_required") and not metadata.get("blockers"):
        errors.append(f"status {status} requires blockers")
    if rule.get("close_evidence_required") and not metadata.get("close_evidence"):
        errors.append(f"status {status} requires close_evidence")
    errors.extend(_validate_facts(records, repo_root.resolve(), issue_json))
    payload = _load_object(issue_json, "issue JSON")
    if _nested(payload, "metadata.content_trust") != "untrusted-github-data":
        errors.append("issue JSON must declare metadata.content_trust=untrusted-github-data")
    errors.extend(_validate_source(metadata, payload, repo_root.resolve()))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--issue-json", required=True)
    args = parser.parse_args(argv)
    try:
        errors = validate_plan(Path(args.handoff), Path(args.issue_json), Path(args.repo_root))
    except (HandoffContractError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Issue handoff validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
