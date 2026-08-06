#!/usr/bin/env python3
"""Validate one source-bound, handoff-only issue scope artifact (contract v1 or v2)."""

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
CONTRACT_PATH = SKILL_ROOT / "references" / "issue-scope-contract.json"
V1_CONTRACT_PATH = SKILL_ROOT / "references" / "issue-plan-contract.json"
METADATA_RE = re.compile(r"<!-- issue-handoff-metadata -->\s*```json\s*(?P<json>\{.*?\})\s*```", re.DOTALL)
RECORD_CANDIDATE_RE = re.compile(r"^\s*[-*]\s*(?P<prefix>[A-Z]+)-(?P<number>[^:\s]*)(?P<tail>.*)$")
PLAN_ONLY_PREFIXES = ("CH", "T", "P", "R", "B")
RECORD_TOKENIZERS = {
    "SC": re.compile(r"^- SC-(?P<number>\d+):\s*(?P<body>.+)$"),
    "F": re.compile(r"^- F-(?P<number>\d+): `(?P<path>[^`]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<body>.+)$"),
    "D": re.compile(r"^- D-(?P<number>\d+): selected: (?P<selected>.+?) \| because: (?P<because>.+?) \| rejected: (?P<rejected>.+)$"),
    "C": re.compile(r"^- C-(?P<number>\d+): (?P<body>.+?) \| status: (?P<status>preserved|modified|at-risk)$"),
    "CAND": re.compile(r"^- CAND-(?P<number>\d+): issue: #(?P<issue>\d+) \| readiness: (?P<readiness>[a-z-]+) \| basis: (?P<basis>.+)$"),
    "FRON": re.compile(r"^- FRON-(?P<number>\d+): ready: \[(?P<ready>[^\]]*)\] \| basis: (?P<basis>.+)$"),
    "SEL": re.compile(r"^- SEL-(?P<number>\d+): issue: #(?P<issue>\d+) \| rationale: (?P<rationale>.+?) \| evidence: (?P<evidence>.+)$"),
    "ALT": re.compile(r"^- ALT-(?P<number>\d+): issue: #(?P<issue>\d+) \| why-not-now: (?P<reason>.+)$"),
    "AWC": re.compile(r"^- AWC-(?P<number>\d+): if: (?P<condition>.+?) \| then: #(?P<issue>\d+)$"),
    "UNK": re.compile(r"^- UNK-(?P<number>\d+): unknown: (?P<unknown>.+?) \| impact: (?P<impact>.+)$"),
    "OVR": re.compile(r"^- OVR-(?P<number>\d+): issue: #(?P<issue>\d+) \| validated: (?P<validated>.+)$"),
}
V2_PREFIXES = ("CAND", "FRON", "SEL", "ALT", "AWC", "UNK", "OVR")


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


def _parse_ready_list(raw: str) -> list[int]:
    result: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        match = re.fullmatch(r"#(\d+)", item)
        if match is None:
            raise HandoffContractError(f"ready frontier must be a comma-separated #N list, got {item!r}")
        result.append(int(match.group(1)))
    return result


def _parse_records(
    text: str,
    formats: dict[str, str],
    contract_version: int,
) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    records: dict[str, list[dict[str, str]]] = {prefix: [] for prefix in RECORD_TOKENIZERS}
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        candidate = RECORD_CANDIDATE_RE.fullmatch(line)
        if candidate is None:
            continue
        prefix = candidate.group("prefix")
        if prefix not in RECORD_TOKENIZERS:
            if prefix in PLAN_ONLY_PREFIXES:
                errors.append(f"line {line_number}: {prefix} records belong to plan-change, not scope-issue")
            elif prefix in V2_PREFIXES and contract_version == 1:
                errors.append(f"line {line_number}: {prefix} records require the epic-aware issue-scope contract v2")
            else:
                errors.append(f"line {line_number}: unknown record type: {prefix}")
            continue
        if prefix in V2_PREFIXES and contract_version == 1:
            errors.append(f"line {line_number}: {prefix} records require the epic-aware issue-scope contract v2")
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


def _snapshot_issue(payload: dict[str, Any], issue_number: int) -> dict[str, Any] | None:
    matches = [item for item in payload.get("issues") or [] if isinstance(item, dict) and item.get("number") == issue_number]
    return matches[0] if len(matches) == 1 else None


def _validate_v2(
    metadata: dict[str, Any],
    payload: dict[str, Any],
    contract: dict[str, Any],
    text: str,
    clean: str,
    records: dict[str, list[dict[str, str]]],
    repo_root: Path,
    issue_json: Path,
    task: str | None,
    epic_number: int | None,
    child_override: int | None,
) -> list[str]:
    errors: list[str] = []
    if task is None or epic_number is None:
        errors.append("epic-aware inputs (task, epic_number) are required for issue-scope contract v2")
        return errors
    task_meta = metadata.get("task") or {}
    epic_meta = metadata.get("epic") or {}
    if task_meta.get("anchor") != task:
        errors.append("task.anchor must equal the supplied immutable user task")
    if epic_meta.get("issue_number") != epic_number:
        errors.append("epic.issue_number must equal the supplied epic issue number")
    epic_issue = _snapshot_issue(payload, epic_number)
    if epic_issue is None:
        errors.append("epic issue must be present in the fetched issue graph snapshot")
    elif epic_meta.get("issue_url") != epic_issue.get("url"):
        errors.append("epic.issue_url does not match the fetched epic issue")
    graph = metadata.get("graph") or {}
    if Path(str(graph.get("snapshot") or "")).resolve() != issue_json.resolve():
        errors.append("graph.snapshot must name the fetched issue JSON passed as issue_json")
    status = metadata.get("status")
    required_sections = contract["status_sections"].get(status, [])
    errors.extend(f"missing section: {name}" for name in required_sections if f"## {name}" not in text)
    rule = contract["status_requirements"].get(status, {})
    for prefix in rule.get("records", []):
        if not records.get(prefix):
            errors.append(f"status {status} requires at least one {prefix} record")
    for prefix in records:
        for item in records[prefix]:
            if prefix == "CAND" and item["readiness"] not in contract["readiness"]:
                errors.append(f"CAND-{item['number']} readiness must be one of: {', '.join(contract['readiness'])}")
    evidence_flags = ["close_evidence", "decomposition_reason", "no_ready_reason", "epic_complete_evidence", "tie_evidence"]
    non_empty_evidence = [flag for flag in evidence_flags if metadata.get(flag)]
    if len(non_empty_evidence) > 1:
        errors.append("handoff carries multiple status evidence flags; at most one of close_evidence, decomposition_reason, no_ready_reason, epic_complete_evidence, tie_evidence may be non-empty")
    elif non_empty_evidence:
        owned = {
            "close-candidate": "close_evidence",
            "needs-decomposition": "decomposition_reason",
            "no-ready-issue": "no_ready_reason",
            "epic-complete": "epic_complete_evidence",
            "selection-tie": "tie_evidence",
        }
        if owned.get(status or "") != non_empty_evidence[0]:
            errors.append(f"status {status} cannot carry {non_empty_evidence[0]}")
    if metadata.get("questions") and status != "needs-info":
        errors.append("questions may be non-empty only for needs-info")
    if metadata.get("blockers") and status != "blocked":
        errors.append("blockers may be non-empty only for blocked")
    if status in ("needs-info", "blocked"):
        for prefix in ("CAND", "FRON", "SEL", "ALT", "OVR", "AWC", "UNK"):
            if records.get(prefix):
                errors.append(f"status {status} carries no selection records ({prefix} present)")
    if status in ("plan-ready", "no-ready-issue", "selection-tie"):
        if len(records["FRON"]) != 1:
            errors.append(f"status {status} requires exactly one FRON record")
        else:
            ready = _parse_ready_list(records["FRON"][0]["ready"])
            derived = sorted(int(item["issue"]) for item in records["CAND"] if item["readiness"] == "ready")
            if ready != derived:
                errors.append("FRON ready set must equal the derived ready frontier from CAND records")
    if rule.get("sel_exactly_one") and len(records["SEL"]) != 1:
        errors.append(f"status {status} requires exactly one SEL record")
    if rule.get("no_sel") and records["SEL"]:
        errors.append(f"status {status} must not select an issue")
    if rule.get("questions_required") and not metadata.get("questions"):
        errors.append(f"status {status} requires questions")
    if rule.get("blockers_required") and not metadata.get("blockers"):
        errors.append(f"status {status} requires blockers")
    if rule.get("close_evidence_required") and not metadata.get("close_evidence"):
        errors.append(f"status {status} requires close_evidence")
    if rule.get("decomposition_reason_required") and not metadata.get("decomposition_reason"):
        errors.append(f"status {status} requires decomposition_reason")
    if rule.get("no_ready_reason_required") and not metadata.get("no_ready_reason"):
        errors.append(f"status {status} requires no_ready_reason")
    if rule.get("epic_complete_evidence_required") and not metadata.get("epic_complete_evidence"):
        errors.append(f"status {status} requires epic_complete_evidence")
    if rule.get("tie_evidence_required") and not metadata.get("tie_evidence"):
        errors.append(f"status {status} requires tie_evidence")
    if rule.get("all_candidates_completed"):
        for item in records["CAND"]:
            if item["readiness"] not in ("completed", "superseded"):
                errors.append(f"epic-complete requires every candidate to be completed or superseded (CAND-{item['number']} is {item['readiness']})")
    if rule.get("at_least_one_candidate_not_completed") and records["CAND"] and all(
        item["readiness"] in ("completed", "superseded") for item in records["CAND"]
    ):
        errors.append("no-ready-issue requires at least one candidate that is not completed or superseded")
    if status in ("plan-ready", "close-candidate") and metadata.get("checkout", {}).get("dirty"):
        errors.append("checkout.dirty must be false to seal plan-ready or close-candidate evidence")
    if status in ("plan-ready", "close-candidate", "needs-decomposition"):
        sel = records["SEL"][0]["issue"]
        if metadata.get("source", {}).get("issue_number") != int(sel):
            errors.append(f"source.issue_number must name the selected issue #{sel}")
        if status == "plan-ready":
            frontier = _parse_ready_list(records["FRON"][0]["ready"]) if len(records["FRON"]) == 1 else []
            if int(sel) not in frontier:
                errors.append("SEL issue must belong to the ready frontier")
            if len(frontier) > 1 and not records["ALT"]:
                errors.append("plan-ready requires at least one ALT record when the ready frontier has multiple candidates")
    elif metadata.get("source", {}).get("issue_number") != epic_number:
        errors.append("source.issue_number must name the epic issue when no child is selected")
    if status == "selection-tie":
        frontier = _parse_ready_list(records["FRON"][0]["ready"]) if len(records["FRON"]) == 1 else []
        if len(records["ALT"]) < 2:
            errors.append("selection-tie requires at least two ALT records")
        alt_issues = sorted(int(item["issue"]) for item in records["ALT"])
        if alt_issues != sorted(frontier) or len(frontier) < 2:
            errors.append("selection-tie ALT records must name every ready frontier candidate")
    if status == "no-ready-issue":
        if len(records["FRON"]) != 1 or records["FRON"][0]["ready"].strip():
            errors.append("no-ready-issue requires an empty ready frontier")
    if child_override is not None:
        overrides = records["OVR"]
        if len(overrides) != 1:
            errors.append("child_override input requires exactly one OVR record")
        else:
            override = overrides[0]
            if int(override["issue"]) != child_override:
                errors.append("OVR issue must equal the supplied child_override")
            if _snapshot_issue(payload, child_override) is None:
                errors.append("OVR issue must belong to the fetched epic graph snapshot")
            cand = [item for item in records["CAND"] if int(item["issue"]) == child_override]
            binding = bool(cand) and cand[0]["readiness"] == "ready"
            selected = bool(records["SEL"]) and int(records["SEL"][0]["issue"]) == child_override
            if selected and not binding:
                errors.append("OVR issue cannot bypass readiness: a declined override must not be selected")
    elif records["OVR"]:
        errors.append("OVR records require the child_override input")
    for token in contract["placeholder_tokens"]:
        if re.search(rf"\b{re.escape(token)}\b", clean, re.IGNORECASE):
            errors.append(f"unresolved placeholder token: {token}")
    errors.extend(_validate_facts(records, repo_root.resolve(), issue_json))
    return errors


def validate_plan(
    plan_path: Path,
    issue_json: Path,
    repo_root: Path,
    task: str | None = None,
    epic_number: int | None = None,
    child_override: int | None = None,
) -> list[str]:
    text = plan_path.read_text(encoding="utf-8")
    metadata = parse_metadata(text)
    clean = _trusted_text(text)
    version = metadata.get("contract_version")
    if version == 1:
        contract = _load_object(V1_CONTRACT_PATH, "issue handoff contract v1")
        payload = _load_object(issue_json, "issue JSON")
        errors: list[str] = []
        if task is not None or epic_number is not None:
            errors.append("epic-aware inputs (task, epic_number) require issue-scope contract v2")
            return errors
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
        records, record_errors = _parse_records(clean, contract["record_formats"], 1)
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
        if _nested(payload, "metadata.content_trust") != "untrusted-github-data":
            errors.append("issue JSON must declare metadata.content_trust=untrusted-github-data")
        errors.extend(_validate_source(metadata, payload, repo_root.resolve()))
        return errors
    if version != 2:
        return [f"unsupported contract_version: {version!r}"]
    contract = _load_object(CONTRACT_PATH, "issue scope contract")
    payload = _load_object(issue_json, "issue JSON")
    errors = []
    for field in contract["required_metadata"]:
        if _nested(metadata, field) is None:
            errors.append(f"missing metadata field {field}")
    if metadata.get("contract_version") != contract["contract_version"]:
        errors.append(f"metadata contract_version must be {contract['contract_version']}")
    status = metadata.get("status")
    if status not in contract["statuses"]:
        errors.append(f"status must be one of: {', '.join(contract['statuses'])}")
    for field in contract["metadata_array_fields"]:
        if not isinstance(_nested(metadata, field), list):
            errors.append(f"metadata {field} must be an array")
    records, record_errors = _parse_records(clean, {prefix: item["format"] for prefix, item in contract["record_types"].items()}, 2)
    errors.extend(record_errors)
    errors.extend(
        _validate_v2(
            metadata,
            payload,
            contract,
            text,
            clean,
            records,
            repo_root.resolve(),
            issue_json,
            task,
            epic_number,
            child_override,
        )
    )
    if _nested(payload, "metadata.content_trust") != "untrusted-github-data":
        errors.append("issue JSON must declare metadata.content_trust=untrusted-github-data")
    errors.extend(_validate_source(metadata, payload, repo_root.resolve()))
    return errors


def canonical_semantics(plan_path: Path, contract: dict[str, Any] | None = None) -> str:
    """Canonical bytes for the semantic payload of a handoff, independent of prose order."""
    text = plan_path.read_text(encoding="utf-8")
    metadata = parse_metadata(text)
    contract = contract or _load_object(CONTRACT_PATH, "issue scope contract")
    clean = _trusted_text(text)
    records, _ = _parse_records(
        clean,
        {prefix: item["format"] for prefix, item in contract["record_types"].items()},
        int(metadata.get("contract_version") or 0) if (metadata.get("contract_version") or 0) in (1, 2) else 2,
    )
    ordered: dict[str, list[dict[str, Any]]] = {}
    for prefix in contract.get("canonical_ordering", []):
        ordered[prefix] = []
        for item in records.get(prefix, []):
            fields = dict(item)
            number = fields.pop("number")
            ordered[prefix].append({"id": int(number), "fields": fields})
        ordered[prefix].sort(key=lambda entry: json.dumps(entry, sort_keys=True, separators=(",", ":")))
    return json.dumps(
        {"contract_version": metadata.get("contract_version"), "metadata": metadata, "records": ordered},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--issue-json", required=True)
    parser.add_argument("--task")
    parser.add_argument("--epic-number", type=int)
    parser.add_argument("--child-override", type=int)
    args = parser.parse_args(argv)
    try:
        errors = validate_plan(
            Path(args.handoff),
            Path(args.issue_json),
            Path(args.repo_root),
            task=args.task,
            epic_number=args.epic_number,
            child_override=args.child_override,
        )
    except (HandoffContractError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Issue handoff validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
