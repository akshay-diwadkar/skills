#!/usr/bin/env python3
"""Validate audit bundles that terminate in a sealed handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
CATEGORIES = {
    "bug",
    "security",
    "performance",
    "test-gap",
    "architecture",
    "maintainability",
    "developer-experience",
}
SEVERITIES = {"critical", "high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
RISK_LEVELS = {"critical", "high", "medium", "low"}
SURFACE_STATUSES = {"accepted", "clean", "rejected", "deferred"}
COVERAGE_STATUSES = {"complete", "not-applicable", "deferred"}
CANDIDATE_DECISIONS = {"accepted", "rejected", "deferred", "merged"}
REPRODUCTION_STATUSES = {"reproduced", "reasoned", "not-run"}
EVIDENCE_KINDS = {"source", "config", "test", "command", "history", "external"}
BASELINE_STATUSES = {"passed", "failed", "not-run"}
DEEP_PATTERNS = {
    "semantic-contract-drift",
    "implicit-ordering-dependency",
    "silent-error-degradation",
    "phantom-cross-reference",
    "temporal-coupling-or-race",
    "boundary-or-encoding-mismatch",
    "default-value-trap",
    "misleading-observability",
    "dependency-graph-shadow",
    "incomplete-lifecycle",
    "boundary-invariant-violation",
    "git-history-risk",
}
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class AuditBundleError(Exception):
    """Raised when an audit bundle is invalid."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditBundleError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditBundleError(f"invalid JSON in {path}: {exc}") from exc


def is_audit_bundle(raw: Any) -> bool:
    return isinstance(raw, dict) and "schema_version" in raw


def _object(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    return value


def _objects(value: Any, path: str, errors: list[str], *, nonempty: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "a non-empty" if nonempty else "an"
        errors.append(f"{path} must be {qualifier} array of objects")
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{path}[{index}] must be an object")
        else:
            result.append(item)
    return result


def _string(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string")
        return ""
    return value.strip()


def _strings(
    obj: dict[str, Any],
    key: str,
    path: str,
    errors: list[str],
    *,
    nonempty: bool = False,
) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "a non-empty" if nonempty else "an"
        errors.append(f"{path}.{key} must be {qualifier} array of strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}.{key}[{index}] must be a non-empty string")
        else:
            result.append(item.strip())
    return result


def _enum(value: Any, allowed: set[str], path: str, errors: list[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{path} must be one of: {', '.join(sorted(allowed))}")
        return ""
    return value


def _unique_id(obj: dict[str, Any], path: str, seen: set[str], errors: list[str]) -> str:
    identifier = _string(obj, "id", path, errors)
    if identifier and identifier in seen:
        errors.append(f"{path}.id duplicates {identifier!r}")
    seen.add(identifier)
    return identifier


def validate_audit_bundle(raw: Any) -> list[str]:
    errors: list[str] = []
    bundle = _object(raw, "bundle", errors)
    if bundle is None:
        return errors

    if bundle.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 2; regenerate or explicitly convert legacy v1 audit bundles")
    legacy_keys = {
        "github_repo_url",
        "issues",
        "output_mode",
        "publication",
        "publish_confirmation",
    }
    for key in sorted(legacy_keys.intersection(bundle)):
        errors.append(
            f"bundle.{key} is not supported in schema v2; "
            "keep publication state outside audit-codebase"
        )

    context = _object(bundle.get("audit_context"), "audit_context", errors) or {}
    _string(context, "target", "audit_context", errors)
    _string(context, "commit", "audit_context", errors)
    if not isinstance(context.get("dirty_worktree"), bool):
        errors.append("audit_context.dirty_worktree must be a boolean")
    categories = _strings(context, "categories", "audit_context", errors, nonempty=True)
    for index, category in enumerate(categories):
        _enum(category, CATEGORIES, f"audit_context.categories[{index}]", errors)
    if len(categories) != len(set(categories)):
        errors.append("audit_context.categories must not contain duplicates")
    threshold = _enum(context.get("severity_threshold"), SEVERITIES, "audit_context.severity_threshold", errors)
    _strings(context, "scope_exclusions", "audit_context", errors)
    limitations = _strings(context, "limitations", "audit_context", errors)

    inventory = _object(bundle.get("repository_inventory"), "repository_inventory", errors) or {}
    _string(inventory, "purpose", "repository_inventory", errors)
    _strings(inventory, "runtimes", "repository_inventory", errors, nonempty=True)
    _strings(inventory, "boundaries", "repository_inventory", errors, nonempty=True)
    _strings(inventory, "generated_or_vendor_paths", "repository_inventory", errors)
    _strings(inventory, "exposed_or_destructive_workflows", "repository_inventory", errors)

    baseline_commands = _objects(
        inventory.get("baseline_commands"), "repository_inventory.baseline_commands", errors, nonempty=True
    )
    for index, command in enumerate(baseline_commands):
        path = f"repository_inventory.baseline_commands[{index}]"
        _string(command, "command", path, errors)
        status = _enum(command.get("status"), BASELINE_STATUSES, f"{path}.status", errors)
        baseline_evidence = _string(command, "evidence", path, errors)
        if status == "not-run" and baseline_evidence and len(baseline_evidence) < 8:
            errors.append(f"{path}.evidence must explain why the command was not run")

    subsystem_ids: set[str] = set()
    subsystems = _objects(inventory.get("subsystems"), "repository_inventory.subsystems", errors, nonempty=True)
    for index, subsystem in enumerate(subsystems):
        path = f"repository_inventory.subsystems[{index}]"
        _unique_id(subsystem, path, subsystem_ids, errors)
        _string(subsystem, "name", path, errors)
        _strings(subsystem, "paths", path, errors, nonempty=True)
        _enum(subsystem.get("risk_level"), RISK_LEVELS, f"{path}.risk_level", errors)

    candidate_ids: set[str] = set()
    accepted_candidate_ids: set[str] = set()
    candidate_decisions: dict[str, str] = {}
    candidate_by_id: dict[str, dict[str, Any]] = {}
    accepted_root_causes: dict[str, str] = {}
    candidates = _objects(bundle.get("candidates"), "candidates", errors)
    for index, candidate in enumerate(candidates):
        path = f"candidates[{index}]"
        candidate_id = _unique_id(candidate, path, candidate_ids, errors)
        candidate_by_id[candidate_id] = candidate
        _string(candidate, "title", path, errors)
        _string(candidate, "summary", path, errors)
        category = _enum(candidate.get("category"), CATEGORIES, f"{path}.category", errors)
        severity = _enum(candidate.get("severity"), SEVERITIES, f"{path}.severity", errors)
        confidence = _enum(candidate.get("confidence"), CONFIDENCE_LEVELS, f"{path}.confidence", errors)
        root_cause = _string(candidate, "root_cause", path, errors)
        _string(candidate, "affected_workflow", path, errors)
        _string(candidate, "impact", path, errors)
        candidate_evidence = _objects(candidate.get("evidence"), f"{path}.evidence", errors, nonempty=True)
        if len(candidate_evidence) < 2:
            errors.append(f"{path}.evidence must contain at least two observations")
        local_evidence = False
        for evidence_index, item in enumerate(candidate_evidence):
            evidence_path = f"{path}.evidence[{evidence_index}]"
            kind = _enum(item.get("kind"), EVIDENCE_KINDS, f"{evidence_path}.kind", errors)
            _string(item, "location", evidence_path, errors)
            _string(item, "observation", evidence_path, errors)
            local_evidence = local_evidence or kind in {"source", "config", "test", "command", "history"}
        if candidate_evidence and not local_evidence:
            errors.append(f"{path}.evidence must contain local evidence")

        reproduction = _object(candidate.get("reproduction"), f"{path}.reproduction", errors) or {}
        reproduction_status = _enum(
            reproduction.get("status"), REPRODUCTION_STATUSES, f"{path}.reproduction.status", errors
        )
        _string(reproduction, "details", f"{path}.reproduction", errors)
        justification = reproduction.get("justification")
        if not isinstance(justification, str):
            errors.append(f"{path}.reproduction.justification must be a string")
        if reproduction_status == "not-run" and (not isinstance(justification, str) or not justification.strip()):
            errors.append(f"{path}.reproduction.justification is required when reproduction is not-run")

        _strings(candidate, "counter_evidence_checked", path, errors, nonempty=True)
        _strings(candidate, "verification", path, errors, nonempty=True)
        _strings(candidate, "acceptance_criteria", path, errors, nonempty=True)
        if not isinstance(candidate.get("independently_fixable"), bool):
            errors.append(f"{path}.independently_fixable must be a boolean")
        decision = _enum(candidate.get("decision"), CANDIDATE_DECISIONS, f"{path}.decision", errors)
        candidate_decisions[candidate_id] = decision
        merged_into = candidate.get("merged_into")
        if not isinstance(merged_into, str):
            errors.append(f"{path}.merged_into must be a string")
        if decision == "merged" and (not isinstance(merged_into, str) or not merged_into.strip()):
            errors.append(f"{path}.merged_into is required when decision is merged")

        if decision == "accepted":
            _strings(candidate, "labels", path, errors, nonempty=True)
            accepted_candidate_ids.add(candidate_id)
            if confidence != "high":
                errors.append(f"{path}.confidence must be high for an accepted candidate")
            if not candidate.get("independently_fixable"):
                errors.append(f"{path}.independently_fixable must be true for an accepted candidate")
            if threshold and severity and SEVERITY_RANK[severity] < SEVERITY_RANK[threshold]:
                errors.append(f"{path}.severity is below the audit threshold {threshold}")
            root_key = root_cause.casefold()
            if root_key in accepted_root_causes:
                errors.append(
                    f"{path}.root_cause duplicates accepted candidate {accepted_root_causes[root_key]!r}"
                )
            elif root_cause:
                accepted_root_causes[root_key] = candidate_id
        if category and categories and category not in categories:
            errors.append(f"{path}.category is outside audit_context.categories")

    reject_ids: set[str] = set()
    rejected_candidate_links: dict[str, int] = {}
    rejects = _objects(bundle.get("rejects"), "rejects", errors)
    for index, reject in enumerate(rejects):
        path = f"rejects[{index}]"
        _unique_id(reject, path, reject_ids, errors)
        candidate_id = _string(reject, "candidate_id", path, errors)
        _string(reject, "reason", path, errors)
        _strings(reject, "evidence", path, errors, nonempty=True)
        if candidate_id not in candidate_ids:
            errors.append(f"{path}.candidate_id references unknown candidate {candidate_id!r}")
        rejected_candidate_links[candidate_id] = rejected_candidate_links.get(candidate_id, 0) + 1

    for candidate_id, decision in candidate_decisions.items():
        reject_count = rejected_candidate_links.get(candidate_id, 0)
        if decision == "accepted" and reject_count:
            errors.append(f"accepted candidate {candidate_id!r} must not have a reject record")
        if decision != "accepted" and reject_count != 1:
            errors.append(f"non-accepted candidate {candidate_id!r} must have exactly one reject record")
        if decision == "merged":
            target = candidate_by_id[candidate_id].get("merged_into")
            if isinstance(target, str) and target and target not in accepted_candidate_ids:
                errors.append(f"merged candidate {candidate_id!r} must target an accepted candidate")

    surface_ids: set[str] = set()
    surface_candidate_links: set[str] = set()
    surface_reject_links: set[str] = set()
    risk_surfaces = _objects(bundle.get("risk_surfaces"), "risk_surfaces", errors, nonempty=True)
    for index, surface in enumerate(risk_surfaces):
        path = f"risk_surfaces[{index}]"
        _unique_id(surface, path, surface_ids, errors)
        _string(surface, "title", path, errors)
        risk_level = _enum(surface.get("risk_level"), RISK_LEVELS, f"{path}.risk_level", errors)
        surface_categories = _strings(surface, "categories", path, errors, nonempty=True)
        for category_index, category in enumerate(surface_categories):
            _enum(category, CATEGORIES, f"{path}.categories[{category_index}]", errors)
        _strings(surface, "locations", path, errors, nonempty=True)
        _strings(surface, "validation_actions", path, errors, nonempty=True)
        status = _enum(surface.get("status"), SURFACE_STATUSES, f"{path}.status", errors)
        linked_candidates = _strings(surface, "candidate_ids", path, errors)
        linked_rejects = _strings(surface, "reject_ids", path, errors)
        _string(surface, "conclusion", path, errors)
        for candidate_id in linked_candidates:
            if candidate_id not in candidate_ids:
                errors.append(f"{path}.candidate_ids references unknown candidate {candidate_id!r}")
            surface_candidate_links.add(candidate_id)
        for reject_id in linked_rejects:
            if reject_id not in reject_ids:
                errors.append(f"{path}.reject_ids references unknown reject {reject_id!r}")
            surface_reject_links.add(reject_id)
        if status == "accepted" and not linked_candidates:
            errors.append(f"{path}.candidate_ids is required when status is accepted")
        if status == "accepted":
            for candidate_id in linked_candidates:
                if candidate_decisions.get(candidate_id) != "accepted":
                    errors.append(f"{path} links non-accepted candidate {candidate_id!r}")
        if status == "rejected" and not linked_rejects:
            errors.append(f"{path}.reject_ids is required when status is rejected")
        if status == "clean" and (linked_candidates or linked_rejects):
            errors.append(f"{path} must not link candidates or rejects when status is clean")
        if status == "deferred" and risk_level in {"high", "critical"} and not limitations:
            errors.append(f"{path} is high-risk and deferred, so audit_context.limitations must explain it")

    coverage_ids: set[str] = set()
    coverage_pairs: set[tuple[str, str]] = set()
    coverage_candidate_links: set[str] = set()
    coverage_reject_links: set[str] = set()
    coverage = _objects(bundle.get("coverage"), "coverage", errors, nonempty=True)
    for index, record in enumerate(coverage):
        path = f"coverage[{index}]"
        _unique_id(record, path, coverage_ids, errors)
        subsystem_id = _string(record, "subsystem_id", path, errors)
        category = _enum(record.get("category"), CATEGORIES, f"{path}.category", errors)
        status = _enum(record.get("status"), COVERAGE_STATUSES, f"{path}.status", errors)
        locations = _strings(record, "locations", path, errors)
        methods = _strings(record, "methods", path, errors)
        linked_candidates = _strings(record, "candidate_ids", path, errors)
        linked_rejects = _strings(record, "reject_ids", path, errors)
        _string(record, "conclusion", path, errors)
        if subsystem_id not in subsystem_ids:
            errors.append(f"{path}.subsystem_id references unknown subsystem {subsystem_id!r}")
        pair = (subsystem_id, category)
        if pair in coverage_pairs:
            errors.append(f"{path} duplicates coverage for subsystem/category {pair!r}")
        coverage_pairs.add(pair)
        if status == "complete" and (not locations or not methods):
            errors.append(f"{path} requires locations and methods when status is complete")
        if status == "deferred" and not limitations:
            errors.append(f"{path} is deferred, so audit_context.limitations must explain it")
        for candidate_id in linked_candidates:
            if candidate_id not in candidate_ids:
                errors.append(f"{path}.candidate_ids references unknown candidate {candidate_id!r}")
            coverage_candidate_links.add(candidate_id)
        for reject_id in linked_rejects:
            if reject_id not in reject_ids:
                errors.append(f"{path}.reject_ids references unknown reject {reject_id!r}")
            coverage_reject_links.add(reject_id)

    required_pairs = {(subsystem_id, category) for subsystem_id in subsystem_ids for category in categories}
    for subsystem_id, category in sorted(required_pairs - coverage_pairs):
        errors.append(f"coverage is missing subsystem/category pair {subsystem_id!r}/{category!r}")
    for subsystem_id, category in sorted(coverage_pairs - required_pairs):
        errors.append(f"coverage contains out-of-scope pair {subsystem_id!r}/{category!r}")

    deep_pattern_ids: set[str] = set()
    deep_candidate_links: set[str] = set()
    deep_reject_links: set[str] = set()
    deep_analysis = _objects(bundle.get("deep_analysis"), "deep_analysis", errors, nonempty=True)
    for index, record in enumerate(deep_analysis):
        path = f"deep_analysis[{index}]"
        pattern = _enum(record.get("pattern"), DEEP_PATTERNS, f"{path}.pattern", errors)
        if pattern in deep_pattern_ids:
            errors.append(f"{path}.pattern duplicates {pattern!r}")
        deep_pattern_ids.add(pattern)
        status = _enum(record.get("status"), COVERAGE_STATUSES, f"{path}.status", errors)
        targets = _strings(record, "targets", path, errors)
        methods = _strings(record, "methods", path, errors)
        linked_candidates = _strings(record, "candidate_ids", path, errors)
        linked_rejects = _strings(record, "reject_ids", path, errors)
        _string(record, "conclusion", path, errors)
        if status == "complete" and (not targets or not methods):
            errors.append(f"{path} requires targets and methods when status is complete")
        if status == "deferred" and not limitations:
            errors.append(f"{path} is deferred, so audit_context.limitations must explain it")
        for candidate_id in linked_candidates:
            if candidate_id not in candidate_ids:
                errors.append(f"{path}.candidate_ids references unknown candidate {candidate_id!r}")
            deep_candidate_links.add(candidate_id)
        for reject_id in linked_rejects:
            if reject_id not in reject_ids:
                errors.append(f"{path}.reject_ids references unknown reject {reject_id!r}")
            deep_reject_links.add(reject_id)
    for pattern in sorted(DEEP_PATTERNS - deep_pattern_ids):
        errors.append(f"deep_analysis is missing pattern {pattern!r}")

    for candidate_id in sorted(accepted_candidate_ids):
        if candidate_id not in surface_candidate_links:
            errors.append(f"accepted candidate {candidate_id!r} is not linked from a risk surface")
        if candidate_id not in coverage_candidate_links:
            errors.append(f"accepted candidate {candidate_id!r} is not linked from coverage")
    linked_reject_ids = surface_reject_links | coverage_reject_links | deep_reject_links
    for reject_id in sorted(reject_ids - linked_reject_ids):
        errors.append(f"reject record {reject_id!r} is not linked from a risk surface or coverage")

    return errors
