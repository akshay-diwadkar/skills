#!/usr/bin/env python3
"""Validate one source-bound, handoff-only GitHub issue artifact.

The v2 contract is epic-aware: given one user task and one epic, the handoff
records a selection stage (candidates, readiness, selection or an honest
non-selection state) and, for the selected child only, a narrowing stage.
All structural rules are read from references/issue-plan-contract.json; this
script verifies declared facts and never chooses semantic priority.
"""

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


class HandoffContractError(ValueError):
    """Raised when trusted source material cannot be reconciled."""


def load_contract() -> dict[str, Any]:
    try:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffContractError(f"unable to read contract: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffContractError("contract must contain a JSON object")
    return value


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


def _has_path(data: dict[str, Any], dotted: str) -> bool:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise HandoffContractError(f"unable to inspect git checkout: {' '.join(args)}") from exc
    return result.stdout.strip()


def _tokenizers(contract: dict[str, Any]) -> dict[str, re.Pattern[str]]:
    return {prefix: re.compile(entry["pattern"]) for prefix, entry in contract["record_formats"].items()}


def _candidate_regex(contract: dict[str, Any]) -> re.Pattern[str]:
    prefixes = sorted(contract["record_formats"], key=len, reverse=True) + contract["forbidden_record_prefixes"]
    return re.compile(r"^\s*[-*]\s*(?P<prefix>" + "|".join(prefixes) + r")-(?P<number>[^:\s]*)(?P<tail>.*)$")


def parse_metadata(text: str) -> dict[str, Any]:
    match = METADATA_RE.search(text)
    if match is None:
        raise HandoffContractError("missing issue-handoff metadata JSON block")
    value = json.loads(match.group("json"))
    if not isinstance(value, dict):
        raise HandoffContractError("issue-handoff metadata must be an object")
    return value


def canonicalize_metadata(text: str) -> str:
    """Re-serialize the metadata JSON block with sorted keys for byte-identical equivalence.

    Only the JSON block is normalized; authored Markdown whitespace is preserved.
    """
    match = METADATA_RE.search(text)
    if match is None:
        return text
    value = json.loads(match.group("json"))
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return text[: match.start("json")] + canonical + text[match.end("json"):]


def _section_bodies(text: str) -> list[tuple[str, str]]:
    headings = list(re.finditer(r"(?m)^## (?P<name>.+?)\s*$", text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections.append((match.group("name"), text[match.end():end]))
    return sections


def _is_subsequence(needles: list[str], haystack: list[str]) -> bool:
    remaining = list(needles)
    for name in haystack:
        if remaining and name == remaining[0]:
            remaining.pop(0)
    return not remaining


def _parse_records(
    text: str,
    contract: dict[str, Any],
    tokenizers: dict[str, re.Pattern[str]],
    candidate_re: re.Pattern[str],
) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    records: dict[str, list[dict[str, str]]] = {prefix: [] for prefix in contract["record_formats"]}
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        candidate = candidate_re.fullmatch(line)
        if candidate is None:
            continue
        prefix = candidate.group("prefix")
        if prefix in contract["forbidden_record_prefixes"]:
            errors.append(f"line {line_number}: {prefix} records belong to plan-change, not scope-issue")
            continue
        match = tokenizers[prefix].fullmatch(line)
        if match is None:
            errors.append(f"line {line_number}: expected {contract['record_formats'][prefix]['format']}")
        else:
            records[prefix].append(match.groupdict())
    numbering = contract["record_numbering"]
    if numbering.get("sequential"):
        for prefix, items in records.items():
            numbers = [int(item["number"]) for item in items]
            start = int(numbering.get("start", 1))
            if numbers and numbers != list(range(start, len(numbers) + start)):
                errors.append(f"{prefix} records must use sequential IDs starting at {start}")
    return records, errors


def _parse_artifact(
    text: str,
    contract: dict[str, Any],
    tokenizers: dict[str, re.Pattern[str]],
    candidate_re: re.Pattern[str],
) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    records: dict[str, list[dict[str, str]]] = {prefix: [] for prefix in contract["record_formats"]}
    errors: list[str] = []
    sections = _section_bodies(text)
    names = [name for name, _body in sections]
    required = list(contract["required_sections"])
    for name in required:
        if name not in names:
            errors.append(f"missing section: {name}")
    for name in required:
        if names.count(name) > 1:
            errors.append(f"section must appear exactly once: {name}")
    if not _is_subsequence(required, names):
        errors.append("required sections must appear in contract order")
    allowed_by_section = {section: [prefix for prefix, owner in contract["record_sections"].items() if owner == section] for section in required}
    line_section: dict[str, str] = {}
    for section_name, section_body in sections:
        for section_line in section_body.splitlines():
            line_section.setdefault(section_line, section_name)
    for line_number, line in enumerate(text.splitlines(), 1):
        candidate = candidate_re.fullmatch(line)
        if candidate is None:
            continue
        prefix = candidate.group("prefix")
        if prefix in contract["forbidden_record_prefixes"]:
            errors.append(f"line {line_number}: {prefix} records belong to plan-change, not scope-issue")
            continue
        section = line_section.get(line)
        if section is None or prefix not in allowed_by_section.get(section, []):
            owners = [owner for owner, owner_prefixes in allowed_by_section.items() if prefix in owner_prefixes]
            errors.append(f"line {line_number}: {prefix} records must appear in their owning section: {', '.join(owners)}")
            continue
        match = tokenizers[prefix].fullmatch(line)
        if match is None:
            errors.append(f"line {line_number}: expected {contract['record_formats'][prefix]['format']}")
        else:
            records[prefix].append(match.groupdict())
    numbering = contract["record_numbering"]
    if numbering.get("sequential"):
        for prefix, items in records.items():
            numbers = [int(item["number"]) for item in items]
            start = int(numbering.get("start", 1))
            if numbers and numbers != list(range(start, len(numbers) + start)):
                errors.append(f"{prefix} records must use sequential IDs starting at {start}")
    return records, errors


def _validate_scope_inputs(inputs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    task = inputs.get("task")
    task_text = task.get("text") if isinstance(task, dict) else None
    task_constraints = task.get("constraints", []) if isinstance(task, dict) else None
    if not isinstance(task_text, str) or not task_text.strip():
        errors.append("scope_inputs.task.text must be a non-empty string")
    elif not isinstance(task_constraints, list) or not all(isinstance(item, str) for item in task_constraints):
        errors.append("scope_inputs.task.constraints must be an array of strings")
    repository = inputs.get("repository")
    try:
        normalized = normalize_github_repo_target(str(repository))
        if normalized != repository:
            errors.append("scope_inputs.repository must normalize to owner/repo")
    except (ConfigError, TypeError):
        errors.append("scope_inputs.repository must be a GitHub owner/repo target")
    epic = inputs.get("epic")
    epic_number = epic.get("number") if isinstance(epic, dict) else None
    epic_url = epic.get("url") if isinstance(epic, dict) else None
    if not isinstance(epic_number, int) or epic_number <= 0:
        errors.append("scope_inputs.epic.number must be a positive integer")
    elif not isinstance(epic_url, str) or not epic_url:
        errors.append("scope_inputs.epic.url must be a non-empty string")
    override = inputs.get("override")
    override_issue = override.get("issue") if isinstance(override, dict) else None
    if override is not None and (not isinstance(override_issue, int) or override_issue <= 0):
        errors.append("scope_inputs.override must be null or an object with a positive issue number")
    if not isinstance(inputs.get("exclusions", []), list) or not all(isinstance(item, int) for item in inputs.get("exclusions", [])):
        errors.append("scope_inputs.exclusions must be an array of issue numbers")
    return errors


def _validate_anchors(metadata: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for label, expected in (
        ("task", inputs.get("task")),
        ("epic", inputs.get("epic")),
        ("override", inputs.get("override")),
        ("exclusions", inputs.get("exclusions", [])),
    ):
        if metadata.get(label) != expected:
            errors.append(f"metadata.{label} does not match scope_inputs.json")
    if metadata.get("source", {}).get("repo") != inputs.get("repository"):
        errors.append("source.repo does not match scope_inputs.repository")
    return errors


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


def _snapshot_issues(payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues = payload.get("issues")
    return [item for item in issues or [] if isinstance(item, dict)]


def _validate_source(metadata: dict[str, Any], payload: dict[str, Any], repo_root: Path, epic: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = metadata.get("source") or {}
    checkout = metadata.get("checkout") or {}
    issues = _snapshot_issues(payload)
    epic_number = epic.get("number") if isinstance(epic, dict) else None
    matches = [item for item in issues if item.get("number") == epic_number]
    if len(matches) != 1:
        return ["source.issue_number must identify exactly one fetched issue (the epic)"]
    issue = matches[0]
    for field, actual, expected in (
        ("source.issue_number", source.get("issue_number"), epic_number),
        ("source.issue_url", source.get("issue_url"), issue.get("url")),
        ("source.issue_updated_at", source.get("issue_updated_at"), issue.get("updated_at")),
        ("source.fetched_at", source.get("fetched_at"), payload.get("fetched_at")),
    ):
        if actual != expected:
            errors.append(f"{field} does not match the fetched snapshot")
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
    actual_dirty = bool(_git(actual_root, "status", "--porcelain"))
    if checkout.get("dirty") != actual_dirty:
        errors.append("checkout.dirty does not match git status")
    return errors


def _validate_status_obligations(
    contract: dict[str, Any],
    status: str,
    metadata: dict[str, Any],
    records: dict[str, list[dict[str, str]]],
    candidates: list[dict[str, str]],
    selections: list[dict[str, str]],
    snapshot_issues: list[dict[str, Any]],
    inputs: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    rule = contract["status_requirements"].get(status)
    if rule is None:
        errors.append(f"status {status} has no obligation rule in the contract")
        return errors
    for field in rule.get("required_fields", []):
        if not metadata.get(field):
            errors.append(f"status {status} requires {field}")
    for field in rule.get("empty_fields", []):
        if metadata.get(field):
            errors.append(f"status {status} cannot carry {field}")
    tie_obligation = rule.get("tie_obligation")
    if tie_obligation and candidates:
        ready_count = sum(1 for candidate in candidates if candidate["readiness"] == "ready")
        questions = metadata.get("questions") or []
        if ready_count >= int(tie_obligation["when_at_least_ready_candidates"]) and not any(tie_obligation["question_must_contain"] in str(question).lower() for question in questions):
            errors.append(
                f"status {status} with {ready_count} ready candidates requires a tie-breaker question mentioning '{tie_obligation['question_must_contain']}'"
            )
    for prefix in rule.get("required_narrowing_records", []):
        if rule.get("narrowing_records_require_sel") and not selections:
            continue
        if not records[prefix]:
            errors.append(f"status {status} requires at least one {prefix} record")
    if rule.get("requires_sel"):
        if len(selections) != 1:
            errors.append(f"status {status} requires exactly one SEL record")
        elif candidates:
            selected = int(selections[0]["issue"])
            matching = [candidate for candidate in candidates if int(candidate["issue"]) == selected]
            if not matching:
                errors.append("SEL issue must be declared as a CAND candidate")
            elif rule.get("sel_readiness") is not None and matching[0]["readiness"] != rule.get("sel_readiness"):
                errors.append("SEL candidate must have readiness 'ready'")
    if rule.get("forbids_sel") and selections:
        errors.append(f"status {status} cannot carry a SEL record")
    readiness_rule = rule.get("candidate_readiness")
    if readiness_rule:
        states = [candidate["readiness"] for candidate in candidates]
        if not states:
            errors.append(f"status {status} requires at least one CAND record")
        if readiness_rule.get("any") and not any(state in readiness_rule["any"] for state in states):
            errors.append(f"status {status} requires at least one candidate with readiness in {readiness_rule['any']}")
        if readiness_rule.get("all") and not all(state in readiness_rule["all"] for state in states):
            errors.append(f"status {status} requires every candidate readiness in {readiness_rule['all']}")
        if readiness_rule.get("none") and any(state in readiness_rule["none"] for state in states):
            errors.append(f"status {status} forbids candidate readiness in {readiness_rule['none']}")
    obligations = contract["selection_stage_obligations"]
    if obligations.get("min_candidates") and not candidates:
        errors.append("selection stage requires at least one CAND record")
    snapshot_numbers = {issue.get("number") for issue in snapshot_issues}
    for candidate in candidates:
        if obligations.get("candidate_issues_must_be_in_snapshot") and int(candidate["issue"]) not in snapshot_numbers:
            errors.append(f"CAND-{candidate['number']} issue #{candidate['issue']} is absent from the fetched snapshot")
        if candidate["readiness"] not in contract["readiness_states"]:
            errors.append(f"CAND-{candidate['number']} readiness must be one of: {', '.join(contract['readiness_states'])}")
    exclusions = set(inputs.get("exclusions", []) or [])
    if selections and obligations.get("sel_cannot_be_excluded") and int(selections[0]["issue"]) in exclusions:
        errors.append("SEL issue must not be excluded by scope_inputs.exclusions")
    if obligations.get("cand_basis_must_cite"):
        for candidate in candidates:
            if not re.search(r"#\d+|\bF-\d+\b", candidate["basis"]):
                errors.append(f"CAND-{candidate['number']} basis must cite a snapshot issue or an F record")
    if selections and obligations.get("sel_alternatives_must_name_other_issue") and len(snapshot_issues) > 1:
        selected = int(selections[0]["issue"])
        named = {int(number) for number in re.findall(r"#(\d+)", selections[0]["alternatives"])}
        if not any(number != selected for number in named):
            errors.append("SEL alternatives must name at least one issue other than the selected issue")
    override = inputs.get("override")
    if override is not None:
        override_issue = int(override["issue"])
        if obligations.get("override_must_be_candidate") and override_issue not in {int(item["issue"]) for item in candidates}:
            errors.append("explicit override issue must be declared as a CAND candidate")
        ready_candidates = {int(item["issue"]): item for item in candidates}
        if obligations.get("override_requires_ready_candidate") and ready_candidates.get(override_issue, {}).get("readiness") != "ready":
            errors.append("explicit override cannot bypass readiness: candidate must be ready")
        if selections and obligations.get("override_requires_ready_candidate") and int(selections[0]["issue"]) != override_issue:
            errors.append("SEL issue must match the explicit override")
    return errors


def validate_plan(plan_path: Path, issue_json: Path, repo_root: Path, scope_inputs: Path) -> list[str]:
    contract = load_contract()
    tokenizers = _tokenizers(contract)
    candidate_re = _candidate_regex(contract)
    text = plan_path.read_text(encoding="utf-8")
    metadata = parse_metadata(text)
    errors: list[str] = []
    for field in contract["required_metadata"]:
        if not _has_path(metadata, field):
            errors.append(f"missing metadata field {field}")
    if metadata.get("contract_version") != contract["contract_version"]:
        errors.append(f"metadata contract_version must be {contract['contract_version']}")
    status = metadata.get("status")
    if status not in contract["statuses"]:
        errors.append(f"status must be one of: {', '.join(contract['statuses'])}")
    for field in ("questions", "blockers", "close_evidence"):
        if not isinstance(metadata.get(field), list) or not all(isinstance(item, str) and item.strip() for item in metadata.get(field, [])):
            errors.append(f"metadata {field} must be an array of non-empty strings")
    if not isinstance(metadata.get("task", {}).get("constraints", []), list):
        errors.append("metadata task.constraints must be an array")
    if not isinstance(metadata.get("exclusions", []), list):
        errors.append("metadata exclusions must be an array")
    if metadata.get("override") is not None and not isinstance(metadata.get("override"), dict):
        errors.append("metadata override must be null or an object")
    body_without_metadata = METADATA_RE.sub("", text)
    for token in contract["placeholder_tokens"]:
        if re.search(rf"\b{re.escape(token)}\b", body_without_metadata, re.IGNORECASE):
            errors.append(f"unresolved placeholder token: {token}")
    records, record_errors = _parse_artifact(text, contract, tokenizers, candidate_re)
    errors.extend(record_errors)
    inputs = _load_object(scope_inputs, "scope inputs JSON")
    errors.extend(_validate_scope_inputs(inputs))
    errors.extend(_validate_anchors(metadata, inputs))
    errors.extend(_validate_facts(records, repo_root.resolve(), issue_json))
    payload = _load_object(issue_json, "issue JSON")
    expected_trust = contract["snapshot_requirements"]["content_trust"]
    if _nested(payload, "metadata.content_trust") != expected_trust:
        errors.append(f"issue JSON must declare metadata.content_trust={expected_trust}")
    if payload.get("repo") != inputs.get("repository"):
        errors.append("snapshot repo does not match scope_inputs.repository")
    epic = inputs.get("epic") or {}
    errors.extend(_validate_source(metadata, payload, repo_root.resolve(), epic))
    candidates = records["CAND"]
    selections = records["SEL"]
    if isinstance(status, str):
        errors.extend(_validate_status_obligations(contract, status, metadata, records, candidates, selections, _snapshot_issues(payload), inputs))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--issue-json", required=True)
    parser.add_argument("--scope-inputs", required=True)
    args = parser.parse_args(argv)
    try:
        errors = validate_plan(Path(args.handoff), Path(args.issue_json), Path(args.repo_root), Path(args.scope_inputs))
    except (HandoffContractError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Issue handoff validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
