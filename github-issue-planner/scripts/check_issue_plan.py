#!/usr/bin/env python3
"""Validate a source-bound GitHub issue planning artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from github_common import ConfigError, normalize_github_repo_target


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = SKILL_ROOT / "references" / "issue-plan-contract.json"
METADATA_RE = re.compile(r"<!-- issue-plan-metadata -->\s*```json\s*(?P<json>\{.*?\})\s*```", re.DOTALL)
RECORD_PATTERNS = {
    "SC": re.compile(r"^- SC-(?P<number>\d+):\s*(?P<body>.+)$", re.MULTILINE),
    "F": re.compile(
        r"^- F-(?P<number>\d+): `(?P<path>[^`]+):(?P<line>\d+)` "
        r"\| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<body>.+)$",
        re.MULTILINE,
    ),
    "D": re.compile(
        r"^- D-(?P<number>\d+): selected: (?P<selected>.+?) \| because: (?P<because>.+?) "
        r"\| rejected: (?P<rejected>.+)$",
        re.MULTILINE,
    ),
    "CH": re.compile(
        r"^- CH-(?P<number>\d+): `(?P<path>[^`]+)` \| anchor: `(?P<anchor>[^`]+)` "
        r"\| status: (?P<status>existing|new) \| change: (?P<body>.+)$",
        re.MULTILINE,
    ),
    "C": re.compile(
        r"^- C-(?P<number>\d+): (?P<body>.+?) \| status: (?P<status>preserved|modified|at-risk)$",
        re.MULTILINE,
    ),
    "T": re.compile(
        r"^- T-(?P<number>\d+): given: (?P<given>.+?) \| expect: (?P<expect>.+?) "
        r"\| command: `(?P<command>[^`]+)`$",
        re.MULTILINE,
    ),
}
SENIOR_REQUIRED_TASKS = {"public-contract", "security", "concurrency", "external-integration"}


class PlanContractError(ConfigError):
    """Raised when an issue-plan artifact violates the contract."""


def run_git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise PlanContractError(f"unable to inspect git checkout: {' '.join(args)}") from exc
    return result.stdout.strip()


def nested_value(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def load_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanContractError(f"unable to read {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanContractError(f"{description} must contain a JSON object")
    return value


def parse_metadata(text: str) -> dict[str, Any]:
    match = METADATA_RE.search(text)
    if not match:
        raise PlanContractError("missing issue-plan metadata JSON block")
    try:
        metadata = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise PlanContractError(f"issue-plan metadata is invalid JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise PlanContractError("issue-plan metadata must be an object")
    return metadata


def trusted_text(text: str) -> str:
    start = text.find("## Issue Claims (Untrusted)")
    end = text.find("## Local Evidence Ledger", start + 1)
    if start == -1 or end == -1:
        return text
    return text[:start] + "## Issue Claims (Untrusted)\n<untrusted-content-removed>\n\n" + text[end:]


def validate_metadata(metadata: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in contract["required_metadata"]:
        if nested_value(metadata, field) is None:
            errors.append(f"missing metadata field {field}")
    if metadata.get("contract_version") != contract["contract_version"]:
        errors.append(f"metadata contract_version must be {contract['contract_version']}")
    status = metadata.get("status")
    if status not in contract["statuses"]:
        errors.append(f"status must be one of: {', '.join(contract['statuses'])}")
    routing = metadata.get("routing")
    if isinstance(routing, dict):
        task_types = routing.get("task_types")
        if not isinstance(task_types, list) or not task_types:
            errors.append("routing.task_types must be a non-empty array")
        elif any(item not in contract["task_types"] for item in task_types):
            errors.append("routing.task_types contains an unsupported task type")
        if routing.get("tier") not in contract["senior_tiers"]:
            errors.append("routing.tier is invalid")
        reasons = routing.get("reasons")
        if not isinstance(reasons, list):
            errors.append("routing.reasons must be an array")
        required_by_risk = (
            isinstance(task_types, list)
            and bool(SENIOR_REQUIRED_TASKS.intersection(task_types))
        ) or routing.get("tier") == "high-risk"
        if required_by_risk and routing.get("senior_required") is not True:
            errors.append("objective high-risk routing must set senior_required to true")
        if status == "ready-for-implementation" and routing.get("senior_required") is not False:
            errors.append("ready-for-implementation requires senior_required false")
        if status == "ready-for-senior-plan" and routing.get("senior_required") is not True:
            errors.append("ready-for-senior-plan requires senior_required true")
    for field in ("open_decisions", "questions", "blockers", "close_evidence"):
        if not isinstance(metadata.get(field), list):
            errors.append(f"metadata {field} must be an array")
    return errors


def validate_sections(text: str, contract: dict[str, Any]) -> list[str]:
    return [f"missing section: {section}" for section in contract["required_sections"] if f"## {section}" not in text]


def parse_records(text: str) -> dict[str, list[dict[str, str]]]:
    return {
        prefix: [match.groupdict() for match in pattern.finditer(text)]
        for prefix, pattern in RECORD_PATTERNS.items()
    }


def validate_record_ids(records: dict[str, list[dict[str, str]]]) -> list[str]:
    errors: list[str] = []
    for prefix, items in records.items():
        numbers = [int(item["number"]) for item in items]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            errors.append(f"{prefix} records must use unique sequential IDs starting at 1")
    return errors


def validate_status_requirements(
    metadata: dict[str, Any],
    records: dict[str, list[dict[str, str]]],
    contract: dict[str, Any],
) -> list[str]:
    status = metadata.get("status")
    if status not in contract["status_requirements"]:
        return []
    rule = contract["status_requirements"][status]
    errors = [f"status {status} requires at least one {prefix} record" for prefix in rule["records"] if not records[prefix]]
    if rule.get("open_decisions_empty") and metadata.get("open_decisions"):
        errors.append(f"status {status} requires no open decisions")
    if rule.get("questions_required") and not metadata.get("questions"):
        errors.append(f"status {status} requires questions")
    if rule.get("blockers_required") and not metadata.get("blockers"):
        errors.append(f"status {status} requires blockers")
    if rule.get("close_evidence_required") and not metadata.get("close_evidence"):
        errors.append(f"status {status} requires close_evidence")
    if rule.get("routing_required"):
        routing = metadata.get("routing") or {}
        if not routing.get("reasons"):
            errors.append(f"status {status} requires routing reasons")
    return errors


def validate_facts(records: dict[str, list[dict[str, str]]], repo_root: Path, issue_json: Path) -> list[str]:
    errors: list[str] = []
    resolved_issue_json = issue_json.resolve()
    for fact in records["F"]:
        raw_path = fact["path"]
        path = (repo_root / raw_path).resolve()
        try:
            path.relative_to(repo_root)
        except ValueError:
            errors.append(f"F-{fact['number']} path escapes the repository")
            continue
        if path == resolved_issue_json or ".scratch" in path.parts:
            errors.append(f"F-{fact['number']} cannot cite remote issue or scratch data as a local fact")
            continue
        if not path.is_file():
            errors.append(f"F-{fact['number']} path does not exist: {raw_path}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        line_number = int(fact["line"])
        if line_number < 1 or line_number > len(lines):
            errors.append(f"F-{fact['number']} line is outside {raw_path}")
        elif fact["anchor"] not in lines[line_number - 1]:
            errors.append(f"F-{fact['number']} anchor is absent from {raw_path}:{line_number}")
    return errors


def selected_issue(payload: dict[str, Any], issue_number: int) -> dict[str, Any]:
    issues = payload.get("issues")
    if not isinstance(issues, list):
        raise PlanContractError("issue JSON lacks issues array")
    matches = [item for item in issues if isinstance(item, dict) and item.get("number") == issue_number]
    if len(matches) != 1:
        raise PlanContractError(f"issue JSON must contain issue #{issue_number} exactly once")
    return matches[0]


def validate_source(
    metadata: dict[str, Any],
    payload: dict[str, Any],
    repo_root: Path,
    execution_ready: bool,
) -> list[str]:
    errors: list[str] = []
    source = metadata.get("source") or {}
    checkout = metadata.get("checkout") or {}
    issue_number = source.get("issue_number")
    if not isinstance(issue_number, int):
        return ["source.issue_number must be an integer"]
    issue = selected_issue(payload, issue_number)
    comparisons = {
        "source.repo": (source.get("repo"), payload.get("repo")),
        "source.issue_url": (source.get("issue_url"), issue.get("url")),
        "source.issue_updated_at": (source.get("issue_updated_at"), issue.get("updated_at")),
    }
    if not execution_ready:
        comparisons["source.fetched_at"] = (source.get("fetched_at"), payload.get("fetched_at"))
    for field, (actual, expected) in comparisons.items():
        if actual != expected:
            errors.append(f"{field} does not match the selected issue JSON")
    metadata_root = Path(str(checkout.get("root") or "")).resolve()
    actual_root = Path(run_git(repo_root, "rev-parse", "--show-toplevel")).resolve()
    if metadata_root != actual_root:
        errors.append("checkout.root does not match --repo-root")
    try:
        remote_repo = normalize_github_repo_target(run_git(actual_root, "remote", "get-url", "origin"))
    except ConfigError as exc:
        errors.append(str(exc))
        remote_repo = ""
    if checkout.get("remote_repo") != remote_repo or source.get("repo") != remote_repo:
        errors.append("checkout origin does not match issue source")
    if execution_ready:
        current_commit = run_git(actual_root, "rev-parse", "HEAD")
        current_dirty = bool(run_git(actual_root, "status", "--porcelain=v1", "--untracked-files=all"))
        if checkout.get("commit") != current_commit:
            errors.append("execution plan is stale because HEAD changed")
        if checkout.get("dirty") is not False or current_dirty:
            errors.append("execution requires a clean checkout planned from a clean snapshot")
    return errors


def validate_senior_plan(
    plan_path: Path,
    issue_plan_path: Path,
    metadata: dict[str, Any],
    repo_root: Path,
    senior_skill_dir: Path,
) -> list[str]:
    if not plan_path.is_file():
        return [f"senior plan not found: {plan_path}"]
    text = plan_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(issue_plan_path.read_bytes()).hexdigest()
    source = metadata["source"]
    checkout = metadata["checkout"]
    required_markers = [
        f"<!-- source-issue-plan-sha256: {digest} -->",
        f"<!-- source-base-commit: {checkout['commit']} -->",
        f"<!-- source-issue-updated-at: {source['issue_updated_at']} -->",
    ]
    errors = [f"senior plan missing source marker: {marker}" for marker in required_markers if marker not in text]
    tier_match = re.search(r"<!--\s*tier:\s*(tiny|standard|high-risk);\s*task-type:", text)
    if not tier_match:
        errors.append("senior plan lacks tier/task marker")
        return errors
    checker = senior_skill_dir / "scripts" / "check_plan.py"
    if not checker.is_file():
        errors.append(f"senior plan checker not found: {checker}")
        return errors
    result = subprocess.run(
        [sys.executable, str(checker), "--tier", tier_match.group(1), "--repo-root", str(repo_root), str(plan_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        errors.append(f"senior plan checker failed: {detail}")
    return errors


def validate_plan(
    plan_path: Path,
    issue_json: Path,
    repo_root: Path,
    execution_ready: bool = False,
    senior_plan: Path | None = None,
    senior_skill_dir: Path | None = None,
) -> list[str]:
    contract = load_json_object(CONTRACT_PATH, "issue-plan contract")
    text = plan_path.read_text(encoding="utf-8")
    metadata = parse_metadata(text)
    clean_text = trusted_text(text)
    errors: list[str] = []
    if contract["marker"] not in text:
        errors.append(f"missing contract marker {contract['marker']}")
    errors.extend(validate_metadata(metadata, contract))
    errors.extend(validate_sections(text, contract))
    for token in contract["placeholder_tokens"]:
        if re.search(rf"\b{re.escape(token)}\b", clean_text, re.IGNORECASE):
            errors.append(f"unresolved placeholder token: {token}")
    records = parse_records(clean_text)
    errors.extend(validate_record_ids(records))
    errors.extend(validate_status_requirements(metadata, records, contract))
    errors.extend(validate_facts(records, repo_root.resolve(), issue_json))
    payload = load_json_object(issue_json, "issue JSON")
    if nested_value(payload, "metadata.content_trust") != "untrusted-github-data":
        errors.append("issue JSON must declare metadata.content_trust=untrusted-github-data")
    errors.extend(validate_source(metadata, payload, repo_root.resolve(), execution_ready))
    if execution_ready:
        status = metadata.get("status")
        if status == "ready-for-implementation":
            if senior_plan is not None:
                errors.append("direct-ready execution must not supply --senior-plan")
        elif status == "ready-for-senior-plan":
            if senior_plan is None:
                errors.append("ready-for-senior-plan execution requires --senior-plan")
            else:
                resolved_skill = senior_skill_dir or SKILL_ROOT.parent / "plan-with-senior-dev"
                errors.extend(
                    validate_senior_plan(senior_plan, plan_path, metadata, repo_root.resolve(), resolved_skill)
                )
        else:
            errors.append(f"status {status} is not execution-eligible")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate one GitHub issue plan.")
    parser.add_argument("plan", help="Issue-plan Markdown file.")
    parser.add_argument("--repo-root", required=True, help="Local checkout used for planning.")
    parser.add_argument("--issue-json", required=True, help="Fresh normalized selected-issue JSON.")
    parser.add_argument("--execution-ready", action="store_true", help="Apply freshness and execution gates.")
    parser.add_argument("--senior-plan", help="Source-bound plan-contract v2 plan for a routed issue.")
    parser.add_argument("--senior-skill-dir", help="Installed plan-with-senior-dev skill directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        errors = validate_plan(
            Path(args.plan).resolve(),
            Path(args.issue_json).resolve(),
            Path(args.repo_root).resolve(),
            execution_ready=args.execution_ready,
            senior_plan=Path(args.senior_plan).resolve() if args.senior_plan else None,
            senior_skill_dir=Path(args.senior_skill_dir).resolve() if args.senior_skill_dir else None,
        )
        if errors:
            print("Issue plan validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
        print("Issue plan validation passed.")
        return 0
    except PlanContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
