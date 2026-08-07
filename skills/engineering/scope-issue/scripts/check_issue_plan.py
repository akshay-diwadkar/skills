#!/usr/bin/env python3
"""Validate one source-bound, handoff-only GitHub issue artifact.

The v2 contract is epic-aware: given one user task and one epic, the handoff
records a selection stage (candidates, readiness, selection or an honest
non-selection state) and, for the selected child only, a narrowing stage.
All structural rules are read from references/issue-plan-contract.json; this
script verifies declared facts and never chooses semantic priority.

The untrusted payload quoted from GitHub must live between machine-owned
fence markers; the fenced span is removed before heading, record, placeholder,
and citation parsing so quoted content is inert. Snapshot membership,
freshness, and digest are verified against the fetched issue JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from github_common import ConfigError, normalize_github_repo_target, snapshot_digest

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


def canonical_body(text: str) -> str:
    """Canonical sealed form: receipt-free input, LF line endings, canonical
    metadata, authored whitespace preserved, EOF normalized to exactly one LF.

    Shared by the sealer and this checker so the receipt can never drift.
    """
    canonical = canonicalize_metadata(text.replace("\r\n", "\n").replace("\r", "\n"))
    if canonical == "":
        return canonical
    return canonical.rstrip("\n") + "\n"


def _strip_untrusted_fence(text: str, contract: dict[str, Any]) -> tuple[str, list[str]]:
    """Remove the machine-owned untrusted span before trusted parsing.

    Both markers must appear exactly once, in order, inside the untrusted
    section: only whitespace may separate the heading from the begin marker
    and the end marker from the next heading. The fenced payload is inert.
    """
    errors: list[str] = []
    fence = contract["untrusted_fence"]
    begin, end = fence["begin"], fence["end"]
    begin_count = text.count(begin)
    end_count = text.count(end)
    if begin_count != 1 or end_count != 1:
        errors.append("untrusted fence requires exactly one begin and one end marker")
        return text, errors
    begin_index = text.find(begin)
    end_index = text.find(end)
    if end_index < begin_index:
        errors.append("untrusted fence begin marker must precede the end marker")
        return text, errors
    heading_re = re.compile(r"(?m)^## " + re.escape(contract["untrusted_section"]) + r"\s*$")
    heading_match = heading_re.search(text[:begin_index])
    if heading_match is None:
        errors.append("untrusted fence must appear inside the Issue Claims (Untrusted) section")
        return text, errors
    gap = text[heading_match.end():begin_index]
    if gap.strip():
        errors.append("content between the untrusted section heading and the begin marker is not allowed")
    next_heading = re.search(r"(?m)^## ", text[end_index + len(end):])
    tail = text[end_index + len(end):]
    gap_end = len(tail) if next_heading is None else next_heading.start()
    if tail[:gap_end].strip():
        errors.append("content between the untrusted end marker and the next section is not allowed")
    stripped = text[:begin_index] + text[end_index + len(end):]
    return stripped, errors


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
    for name in names:
        if name not in required:
            errors.append(f"section not part of the contract: {name}")
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
    mode = inputs.get("mode")
    allowed_modes = ("single", "index")
    if mode not in allowed_modes:
        errors.append(f"scope_inputs.mode must be one of: {', '.join(allowed_modes)}")
    return errors


def _validate_anchors(metadata: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for label, expected in (
        ("task", inputs.get("task")),
        ("override", inputs.get("override")),
        ("exclusions", inputs.get("exclusions", [])),
    ):
        if metadata.get(label) != expected:
            errors.append(f"metadata.{label} does not match scope_inputs.json")
    metadata_epic = metadata.get("epic")
    inputs_epic = inputs.get("epic")
    if (
        not isinstance(metadata_epic, dict)
        or not isinstance(inputs_epic, dict)
        or metadata_epic.get("number") != inputs_epic.get("number")
        or metadata_epic.get("url") != inputs_epic.get("url")
    ):
        errors.append("metadata.epic does not match scope_inputs.json")
    if metadata.get("mode") != inputs.get("mode"):
        errors.append("metadata.mode does not match scope_inputs.mode")
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
    if isinstance(epic, dict) and epic.get("url") != issue.get("url"):
        errors.append("epic.url must exactly match the snapshot issue url")
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
    porcelain = _git(actual_root, "status", "--porcelain")
    actual_dirty = bool(porcelain)
    if checkout.get("dirty") != actual_dirty:
        errors.append("checkout.dirty does not match git status")
    actual_fingerprint = hashlib.sha256(porcelain.rstrip("\n").encode("utf-8")).hexdigest()
    if checkout.get("dirty_fingerprint") != actual_fingerprint:
        errors.append("checkout.dirty_fingerprint does not match git status")
    return errors


def _validate_snapshot_digest(metadata: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    computed = snapshot_digest(payload)
    if payload.get("digest") != computed:
        errors.append("snapshot digest does not match its content")
    if metadata.get("source", {}).get("snapshot_digest") != computed:
        errors.append("source.snapshot_digest does not match the fetched snapshot digest")
    return errors


def _validate_freshness(payload: dict[str, Any], candidates: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    fetched_at = payload.get("fetched_at")
    issues_by_number = {issue.get("number"): issue for issue in _snapshot_issues(payload)}
    for candidate in candidates:
        issue = issues_by_number.get(int(candidate["issue"]))
        if issue is None:
            continue
        updated_at = issue.get("updated_at")
        if isinstance(fetched_at, str) and isinstance(updated_at, str) and updated_at > fetched_at:
            errors.append(f"CAND-{candidate['number']} issue #{candidate['issue']} is stale: updated_at postdates fetched_at")
    return errors


def _validate_membership(
    contract: dict[str, Any],
    payload: dict[str, Any],
    epic_number: int,
    candidates: list[dict[str, str]],
    exclusions: list[int],
) -> list[str]:
    errors: list[str] = []
    requirements = contract["snapshot_requirements"]["membership"]
    membership = payload.get("membership")
    if not isinstance(membership, dict):
        errors.append("snapshot must declare a membership object")
        return errors
    completeness = membership.get("candidate_completeness")
    if completeness not in requirements["completeness_states"]:
        errors.append(f"membership.candidate_completeness must be one of: {', '.join(requirements['completeness_states'])}")
        return errors
    children_of = membership.get("children_of")
    provenance = membership.get("provenance")
    if not isinstance(children_of, dict):
        errors.append("membership.children_of must be an object mapping epic issue numbers to child lists")
        children_of = {}
    if not isinstance(provenance, dict):
        errors.append("membership.provenance must be an object")
        provenance = {}
    snapshot_numbers = {issue.get("number") for issue in _snapshot_issues(payload)}
    if completeness == "verified":
        mechanism = provenance.get("mechanism")
        derived_at = provenance.get("derived_at")
        if not (isinstance(mechanism, str) and mechanism.strip()):
            errors.append("verified membership requires a non-empty provenance.mechanism")
        if not (isinstance(derived_at, str) and derived_at.strip()):
            errors.append("verified membership requires a non-empty provenance.derived_at")
        children = children_of.get(str(epic_number), children_of.get(epic_number, []))
        if not isinstance(children, list) or not all(isinstance(child, int) for child in children):
            errors.append(f"membership.children_of[{epic_number}] must be a list of issue numbers")
            children = []
        issues_by_number = {issue.get("number"): issue for issue in _snapshot_issues(payload)}
        for child in children:
            if issues_by_number.get(child) is None:
                errors.append(f"verified child #{child} is absent from the fetched snapshot")
        if requirements["verified"].get("cand_must_equal_children_minus_exclusions"):
            expected = {child for child in children if child not in exclusions}
            actual = {int(candidate["issue"]) for candidate in candidates}
            if actual != expected:
                errors.append(f"CAND issues must equal verified children minus exclusions ({sorted(expected)})")
        if requirements["verified"].get("exclusions_must_name_children") and not set(exclusions) <= set(children):
            errors.append("scope_inputs.exclusions must name verified children of the epic")
    else:
        if requirements["unverified"].get("children_must_be_empty") and children_of:
            errors.append("unverified membership requires an empty children_of object")
        if requirements["unverified"].get("mechanism_must_be_null") and provenance.get("mechanism") is not None:
            errors.append("unverified membership requires a null provenance.mechanism")
        if requirements["unverified"].get("derived_at_must_be_null") and provenance.get("derived_at") is not None:
            errors.append("unverified membership requires a null provenance.derived_at")
        if requirements["unverified"].get("exclusions_must_name_snapshot_issues"):
            for exclusion in exclusions:
                if exclusion not in snapshot_numbers:
                    errors.append(f"scope_inputs.exclusions {exclusion} must name a snapshot issue")
    return errors


def _validate_alternatives(sel: dict[str, str], candidates: list[dict[str, str]], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    obligations = contract["selection_stage_obligations"]["sel_alternatives"]
    selected = int(sel["issue"])
    ready_others = [candidate for candidate in candidates if candidate["readiness"] == "ready" and int(candidate["issue"]) != selected]
    raw = sel["alternatives"].strip()
    if raw == "none":
        if obligations.get("none_when_sole_ready_candidate") and ready_others:
            errors.append(f"SEL-{sel['number']} alternatives must be 'none' only when no other ready candidate exists")
        return errors
    parts = [part.strip() for part in raw.split(",")]
    if not parts or any(not part for part in parts):
        errors.append(f"SEL-{sel['number']} alternatives must use: CAND-n why-not-now: <reason>[, ...] or none")
        return errors
    named: list[str] = []
    for part in parts:
        match = re.fullmatch(r"CAND-(\d+) why-not-now: (.+)", part)
        if match is None:
            errors.append(f"SEL-{sel['number']} alternatives must use: CAND-n why-not-now: <reason>")
            continue
        cand_number, reason = match.group(1), match.group(2).strip()
        candidate = next((item for item in candidates if item["number"] == cand_number), None)
        if candidate is None:
            errors.append(f"SEL-{sel['number']} alternatives must name declared CAND records")
            continue
        if int(candidate["issue"]) == selected:
            errors.append(f"SEL-{sel['number']} alternatives must not name the selected candidate")
        if candidate["readiness"] != "ready":
            errors.append(f"SEL-{sel['number']} alternatives must name only other ready candidates")
        if not reason:
            errors.append(f"SEL-{sel['number']} alternatives reasons must be non-empty")
        named.append(cand_number)
    if len(set(named)) != len(named):
        errors.append(f"SEL-{sel['number']} alternatives must not name a candidate twice")
    if obligations.get("exhaustive_over_other_ready_candidates"):
        expected = sorted(candidate["number"] for candidate in ready_others)
        if sorted(named) != expected:
            errors.append(f"SEL-{sel['number']} alternatives must name every other ready candidate exactly once: {expected}")
    return errors


def _validate_override_membership(
    contract: dict[str, Any],
    payload: dict[str, Any],
    inputs: dict[str, Any],
    epic_number: int,
) -> list[str]:
    errors: list[str] = []
    override = inputs.get("override")
    if override is None:
        return errors
    override_issue = int(override["issue"])
    membership = payload.get("membership")
    completeness = membership.get("candidate_completeness") if isinstance(membership, dict) else None
    if completeness == "verified":
        children_of = membership.get("children_of") if isinstance(membership, dict) else {}
        children = children_of.get(str(epic_number), children_of.get(epic_number, [])) if isinstance(children_of, dict) else []
        if not isinstance(children, list) or override_issue not in children:
            errors.append("explicit override issue must be a verified child of the epic")
    else:
        snapshot_numbers = {issue.get("number") for issue in _snapshot_issues(payload)}
        if override_issue not in snapshot_numbers:
            errors.append("explicit override issue must exist in the snapshot issues array")
    return errors


def _validate_citations(
    trusted_text: str,
    contract: dict[str, Any],
    records: dict[str, list[dict[str, str]]],
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    snapshot_numbers = {issue.get("number") for issue in _snapshot_issues(payload)}
    f_numbers = {int(item["number"]) for item in records["F"]}
    allowed_sections = set(contract["section_order"]) - {
        "Plan-Change Handoff",
        "Risks and Open Questions",
        contract["untrusted_section"],
    }
    for section_name, section_body in _section_bodies(trusted_text):
        if section_name not in allowed_sections:
            continue
        for raw_number in re.findall(r"#(\d+)", section_body):
            if int(raw_number) not in snapshot_numbers:
                errors.append(f"citation #{raw_number} in {section_name} does not resolve to a snapshot issue")
        for raw_number in re.findall(r"F-(\d+)", section_body):
            if int(raw_number) not in f_numbers:
                errors.append(f"citation F-{raw_number} in {section_name} does not match a declared F record")
    for field in ("blockers", "close_evidence"):
        for entry in metadata.get(field) or []:
            for raw_number in re.findall(r"#(\d+)", entry):
                if int(raw_number) not in snapshot_numbers:
                    errors.append(f"{field} citation #{raw_number} does not resolve to a snapshot issue")
            for raw_number in re.findall(r"F-(\d+)", entry):
                if int(raw_number) not in f_numbers:
                    errors.append(f"{field} citation F-{raw_number} does not match a declared F record")
    return errors


def _blocker_cites(blockers: list[Any], numbers: set[int]) -> bool:
    for blocker in blockers:
        if any(int(raw) in numbers for raw in re.findall(r"#(\d+)", str(blocker))):
            return True
    return False


def _validate_status_obligations(
    contract: dict[str, Any],
    status: str,
    metadata: dict[str, Any],
    records: dict[str, list[dict[str, str]]],
    candidates: list[dict[str, str]],
    selections: list[dict[str, str]],
    snapshot_issues: list[dict[str, Any]],
    inputs: dict[str, Any],
    zero_candidates_allowed: bool = False,
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
    stages = rule.get("sel_stages")
    if stages:
        stage_name = "narrowing" if selections else "pre_selection"
        stage = stages[stage_name]
        for prefix in stage.get("required_narrowing_records", []):
            if not records[prefix]:
                errors.append(f"status {status} requires at least one {prefix} record")
        for prefix in stage.get("forbidden_narrowing_records", []):
            if records[prefix]:
                errors.append(f"status {status} cannot carry {prefix} records before a selection is made")
        evidence = stage.get("blocker_evidence")
        if evidence and metadata.get("blockers"):
            epic_number = inputs.get("epic", {}).get("number")
            if stage_name == "narrowing":
                required = {int(selections[0]["issue"])}
                if not _blocker_cites(metadata["blockers"], required):
                    errors.append("status blocked narrowing requires a blocker citing the selected child's issue")
            else:
                targets = {epic_number} | {int(candidate["issue"]) for candidate in candidates}
                if not _blocker_cites(metadata["blockers"], targets):
                    errors.append("status blocked pre-selection requires a blocker citing the epic issue or a declared candidate")
    elif not selections:
        for prefix in rule.get("forbidden_narrowing_records", []):
            if records[prefix]:
                errors.append(f"status {status} cannot carry {prefix} records without a selection")
    for prefix in rule.get("required_narrowing_records", []):
        if rule.get("narrowing_records_require_sel") and not selections:
            continue
        if not records[prefix]:
            errors.append(f"status {status} requires at least one {prefix} record")
    if rule.get("requires_sel") and len(selections) != 1:
        errors.append(f"status {status} requires exactly one SEL record")
    if rule.get("forbids_sel") and selections:
        errors.append(f"status {status} cannot carry a SEL record")
    tie_obligation = rule.get("tie_obligation")
    if tie_obligation and candidates:
        ready_count = sum(1 for candidate in candidates if candidate["readiness"] == "ready")
        questions = metadata.get("questions") or []
        reason = tie_obligation["requires_reason"]
        tie_questions = [item for item in questions if isinstance(item, dict) and item.get("reason") == reason]
        threshold = int(tie_obligation["when_at_least_ready_candidates"])
        if ready_count >= threshold and not tie_questions:
            errors.append(
                f"status {status} with {ready_count} ready candidates requires a tie-breaker question with reason '{reason}'"
            )
    decomposition_target_rule = rule.get("decomposition_target")
    if decomposition_target_rule:
        target = metadata.get("decomposition_target")
        match = re.fullmatch(r"CAND-(\d+)", str(target or ""))
        if match is None:
            errors.append(f"status {status} requires decomposition_target like CAND-n")
        else:
            candidate = next((item for item in candidates if item["number"] == match.group(1)), None)
            if candidate is None:
                errors.append("decomposition_target must reference a declared CAND record")
            else:
                if candidate["readiness"] != decomposition_target_rule["target_readiness"]:
                    errors.append("decomposition_target candidate must have readiness 'needs-decomposition'")
                if int(candidate["issue"]) in inputs.get("exclusions", []):
                    errors.append("decomposition_target candidate must not be excluded")
    readiness_rule = rule.get("candidate_readiness")
    if readiness_rule:
        states = [candidate["readiness"] for candidate in candidates]
        if not states and not zero_candidates_allowed:
            errors.append(f"status {status} requires at least one CAND record")
        if readiness_rule.get("any") and not any(state in readiness_rule["any"] for state in states):
            errors.append(f"status {status} requires at least one candidate with readiness in {readiness_rule['any']}")
        if readiness_rule.get("all") and not all(state in readiness_rule["all"] for state in states):
            errors.append(f"status {status} requires every candidate readiness in {readiness_rule['all']}")
        if readiness_rule.get("none") and any(state in readiness_rule["none"] for state in states):
            errors.append(f"status {status} forbids candidate readiness in {readiness_rule['none']}")
    obligations = contract["selection_stage_obligations"]
    if obligations.get("min_candidates") and not candidates and not zero_candidates_allowed:
        errors.append("selection stage requires at least one CAND record")
    snapshot_numbers = {issue.get("number") for issue in snapshot_issues}
    for candidate in candidates:
        if obligations.get("candidate_issues_must_be_in_snapshot") and int(candidate["issue"]) not in snapshot_numbers:
            errors.append(f"CAND-{candidate['number']} issue #{candidate['issue']} is absent from the fetched snapshot")
        if candidate["readiness"] not in contract["readiness_states"]:
            errors.append(f"CAND-{candidate['number']} readiness must be one of: {', '.join(contract['readiness_states'])}")
    exclusions = set(inputs.get("exclusions", []) or [])
    for candidate in candidates:
        if obligations.get("cand_cannot_be_excluded") and int(candidate["issue"]) in exclusions:
            errors.append(f"CAND-{candidate['number']} issue must not be excluded by scope_inputs.exclusions")
    if selections and obligations.get("sel_cannot_be_excluded") and int(selections[0]["issue"]) in exclusions:
        errors.append("SEL issue must not be excluded by scope_inputs.exclusions")
    if selections and obligations.get("sel_issue_must_be_candidate"):
        if int(selections[0]["issue"]) not in {int(candidate["issue"]) for candidate in candidates}:
            errors.append("SEL issue must be declared as a CAND candidate")
    if selections and obligations.get("sel_requires_ready_candidate"):
        matching = [candidate for candidate in candidates if int(candidate["issue"]) == int(selections[0]["issue"])]
        if matching and matching[0]["readiness"] != "ready":
            errors.append("SEL candidate must have readiness 'ready'")
    if obligations.get("cand_basis_must_cite"):
        for candidate in candidates:
            if not re.search(r"#\d+|\bF-\d+\b", candidate["basis"]):
                errors.append(f"CAND-{candidate['number']} basis must cite a snapshot issue or an F record")
    for sel in selections:
        errors.extend(_validate_alternatives(sel, candidates, contract))
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
    metadata_mode = metadata.get("mode")
    allowed_modes = contract["snapshot_requirements"]["mode"]["values"]
    if metadata_mode not in allowed_modes:
        errors.append(f"metadata.mode must be one of: {', '.join(allowed_modes)}")
    epic_meta = metadata.get("epic")
    if not isinstance(epic_meta, dict) or not isinstance(epic_meta.get("purpose"), str) or not epic_meta["purpose"].strip():
        errors.append("metadata epic.purpose must be a non-empty string")
    if metadata.get("confidence") not in contract["confidence_levels"]:
        errors.append(f"metadata confidence must be one of: {', '.join(contract['confidence_levels'])}")
    for field in ("unknowns", "alternate_winners"):
        if field not in metadata:
            continue
        if not isinstance(metadata[field], list) or not all(isinstance(item, str) and item.strip() for item in metadata[field]):
            errors.append(f"metadata {field} must be an array of non-empty strings")
    for field in ("blockers", "close_evidence"):
        if not isinstance(metadata.get(field), list) or not all(isinstance(item, str) and item.strip() for item in metadata.get(field, [])):
            errors.append(f"metadata {field} must be an array of non-empty strings")
    questions = metadata.get("questions")
    if not isinstance(questions, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("question"), str)
        and item["question"].strip()
        and item.get("reason") in contract["question_reason_codes"]
        for item in questions
    ):
        codes = ", ".join(contract["question_reason_codes"])
        errors.append(f"metadata questions must be an array of {{question, reason}} objects with reason in: {codes}")
    if not isinstance(metadata.get("task", {}).get("constraints", []), list):
        errors.append("metadata task.constraints must be an array")
    if not isinstance(metadata.get("exclusions", []), list):
        errors.append("metadata exclusions must be an array")
    if metadata.get("override") is not None and not isinstance(metadata.get("override"), dict):
        errors.append("metadata override must be null or an object")
    trusted_text, fence_errors = _strip_untrusted_fence(text, contract)
    errors.extend(fence_errors)
    body_without_metadata = METADATA_RE.sub("", trusted_text)
    for token in contract["placeholder_tokens"]:
        if re.search(rf"\b{re.escape(token)}\b", body_without_metadata, re.IGNORECASE):
            errors.append(f"unresolved placeholder token: {token}")
    records, record_errors = _parse_artifact(trusted_text, contract, tokenizers, candidate_re)
    errors.extend(record_errors)
    inputs = _load_object(scope_inputs, "scope inputs JSON")
    errors.extend(_validate_scope_inputs(inputs))
    errors.extend(_validate_anchors(metadata, inputs))
    errors.extend(_validate_facts(records, repo_root.resolve(), issue_json))
    payload = _load_object(issue_json, "issue JSON")
    expected_trust = contract["snapshot_requirements"]["content_trust"]
    if _nested(payload, "metadata.content_trust") != expected_trust:
        errors.append(f"issue JSON must declare metadata.content_trust={expected_trust}")
    mode = _nested(payload, "metadata.mode")
    if mode not in allowed_modes:
        errors.append(f"snapshot metadata.mode must be one of: {', '.join(allowed_modes)}")
    if mode != metadata_mode:
        errors.append("metadata.mode does not match the snapshot mode")
    if payload.get("repo") != inputs.get("repository"):
        errors.append("snapshot repo does not match scope_inputs.repository")
    epic = inputs.get("epic") or {}
    errors.extend(_validate_source(metadata, payload, repo_root.resolve(), epic))
    errors.extend(_validate_snapshot_digest(metadata, payload))
    candidates = records["CAND"]
    selections = records["SEL"]
    if len(selections) > 1:
        errors.append("at most one SEL record is allowed per artifact")
    if selections and "alternate_winners" not in metadata:
        errors.append("alternate_winners is required when a SEL record exists")
    if not selections and "alternate_winners" in metadata:
        errors.append("alternate_winners is only valid when a SEL record exists")
    candidate_issues = [int(candidate["issue"]) for candidate in candidates]
    if len(candidate_issues) != len(set(candidate_issues)):
        errors.append("CAND issues must be unique across the artifact")
    exclusions = inputs.get("exclusions", []) or []
    epic_number = epic.get("number") if isinstance(epic, dict) else None
    zero_candidates_allowed = False
    if isinstance(epic_number, int) and status == "epic-complete":
        membership = payload.get("membership")
        children_of = membership.get("children_of") if isinstance(membership, dict) else None
        if (
            isinstance(membership, dict)
            and membership.get("candidate_completeness") == "verified"
            and isinstance(children_of, dict)
        ):
            children = children_of.get(str(epic_number), children_of.get(epic_number, []))
            if isinstance(children, list) and set(children) <= set(exclusions):
                zero_candidates_allowed = True
    if isinstance(epic_number, int):
        errors.extend(_validate_membership(contract, payload, epic_number, candidates, exclusions))
        errors.extend(_validate_override_membership(contract, payload, inputs, epic_number))
        if mode == "single":
            single = contract["single_issue_mode"]
            issues = _snapshot_issues(payload)
            if single.get("snapshot_count_must_be_one") and (payload.get("count") != 1 or len(issues) != 1):
                errors.append("single-issue mode requires exactly one snapshot issue")
            if single.get("epic_must_be_the_single_issue") and not (len(issues) == 1 and issues[0].get("number") == epic_number):
                errors.append("single-issue mode requires the epic to be the single snapshot issue")
            if single.get("exactly_one_candidate_naming_the_issue") and candidate_issues != [epic_number]:
                errors.append("single-issue mode requires exactly one CAND record naming the epic issue")
            if single.get("override_must_be_null") and inputs.get("override") is not None:
                errors.append("single-issue mode forbids an override")
            if single.get("exclusions_must_be_empty") and exclusions:
                errors.append("single-issue mode forbids exclusions")
    errors.extend(_validate_freshness(payload, candidates))
    if isinstance(status, str):
        errors.extend(_validate_status_obligations(contract, status, metadata, records, candidates, selections, _snapshot_issues(payload), inputs, zero_candidates_allowed=zero_candidates_allowed))
    tie_reason = contract["question_reason_codes"][0]
    ready_count = sum(1 for candidate in candidates if candidate["readiness"] == "ready")
    if isinstance(questions, list) and any(isinstance(item, dict) and item.get("reason") == tie_reason for item in questions) and ready_count < 2:
        errors.append(f"cannot carry a '{tie_reason}' question with fewer than 2 ready candidates")
    errors.extend(_validate_citations(trusted_text, contract, records, payload, metadata))
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
