#!/usr/bin/env python3
"""Validate a Markdown manual against a source-bound manualize bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft7Validator

SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_SCHEMA = SKILL_ROOT / "schemas" / "manual-bundle.schema.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _error(error_type: str, location: str, severity: str, message: str) -> dict[str, str]:
    return {"type": error_type, "location": location, "severity": severity, "message": message}


def _schema_errors(data: Any) -> list[dict[str, str]]:
    try:
        schema = json.loads(BUNDLE_SCHEMA.read_text(encoding="utf-8"))
        schema["properties"]["glossary"] = json.loads(
            (BUNDLE_SCHEMA.parent / "glossary.schema.json").read_text(encoding="utf-8")
        )
        schema["properties"]["validation_receipt"] = json.loads(
            (BUNDLE_SCHEMA.parent / "validation-receipt.schema.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read bundle schema: {exc}") from exc
    errors = sorted(Draft7Validator(schema).iter_errors(data), key=lambda item: list(item.absolute_path))
    result = []
    for item in errors:
        location = ".".join(str(part) for part in item.absolute_path) or "$"
        result.append(_error("invalid_bundle", location, "critical", item.message))
    return result


def load_bundle(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read bundle: {exc}") from exc
    errors = _schema_errors(data)
    if errors:
        raise ValueError("; ".join(f"{item['location']}: {item['message']}" for item in errors))
    assert isinstance(data, dict)
    return data


def _section_bounds(text: str) -> dict[str, tuple[int, int]]:
    headings = list(re.finditer(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", text))
    sections: dict[str, tuple[int, int]] = {"document": (0, len(text))}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[match.group(1).strip().casefold()] = (match.end(), end)
    return sections


def _scope(text: str, section: str | None, sections: dict[str, tuple[int, int]]) -> tuple[str, int, str]:
    if not section:
        return text, 0, "document"
    bounds = sections.get(section.casefold())
    if bounds is None:
        return "", 0, f"section {section}"
    start, end = bounds
    return text[start:end], start, f"section {section}"


def _tokenize_command(value: str) -> list[str]:
    try:
        return shlex.split(value, posix=True)
    except ValueError:
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', value)


def _changed_command(manual: str, literal: str) -> bool:
    expected = sorted(_tokenize_command(literal))
    if len(expected) < 2:
        return False
    for line in manual.splitlines():
        candidate = line.strip().strip("`")
        if candidate != literal and sorted(_tokenize_command(candidate)) == expected:
            return True
    return False


def _safe_source(repo_root: Path, relative: str) -> Path | None:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        return None
    candidate = (repo_root / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return None
    return candidate


def validate_manual(text: str, bundle: dict[str, Any], repo_root: Path) -> list[dict[str, str]]:
    """Return stable semantic diagnostics without modifying any input."""
    root = repo_root.resolve()
    sections = _section_bounds(text)
    errors: list[dict[str, str]] = []

    for source in bundle["sources"]:
        location = f"source {source['id']}"
        path = _safe_source(root, source["path"])
        if path is None:
            errors.append(_error("unsafe_source_path", location, "critical", f"Source path escapes repo root: {source['path']}"))
            continue
        if not path.is_file():
            errors.append(_error("missing_source", location, "critical", f"Source file does not exist: {source['path']}"))
            continue
        actual = sha256_bytes(path.read_bytes())
        if actual != source["sha256"]:
            errors.append(_error("source_hash_mismatch", location, "critical", f"Source hash changed: {source['path']}"))

    for fact in bundle.get("required_facts", []):
        scoped, _, location = _scope(text, fact.get("section"), sections)
        if fact["claim"] not in scoped:
            errors.append(_error("missing_required_fact", location, "error", f"Missing fact {fact['id']}: {fact['claim']}"))

    for item in bundle.get("integrity_literals", []):
        scoped, _, location = _scope(text, item.get("section"), sections)
        if item["literal"] in scoped:
            continue
        error_type = f"changed_{item['kind']}"
        if item["kind"] == "command" and not _changed_command(scoped, item["literal"]):
            error_type = "missing_command"
        elif item["kind"] != "command":
            error_type = f"missing_{item['kind']}"
        errors.append(_error(error_type, location, "critical", f"Required {item['kind']} changed or is missing: {item['literal']}"))

    for procedure in bundle.get("procedures", []):
        scoped, _, location = _scope(text, procedure.get("section"), sections)
        positions = [scoped.find(marker) for marker in procedure["ordered_markers"]]
        missing = [marker for marker, position in zip(procedure["ordered_markers"], positions, strict=True) if position < 0]
        if missing:
            errors.append(_error("missing_procedure_step", location, "critical", f"Procedure {procedure['id']} is missing: {missing[0]}"))
        elif positions != sorted(positions):
            errors.append(_error("procedure_order", location, "critical", f"Procedure {procedure['id']} is out of order"))

    for warning in bundle.get("warnings", []):
        scoped, _, location = _scope(text, warning.get("section"), sections)
        warning_at = scoped.find(warning["warning"])
        action_at = scoped.find(warning["dangerous_action"])
        if action_at < 0:
            errors.append(_error("missing_dangerous_action", location, "error", f"Bound action is missing: {warning['dangerous_action']}"))
        elif warning_at < 0:
            errors.append(_error("missing_warning", location, "critical", f"Warning {warning['id']} is missing"))
        elif warning_at > action_at:
            errors.append(_error("warning_order", location, "critical", f"Warning {warning['id']} follows the dangerous action"))

    for recovery in bundle.get("recovery_steps", []):
        scoped, _, location = _scope(text, recovery.get("section"), sections)
        if recovery["step"] not in scoped:
            errors.append(_error("missing_recovery_step", location, "critical", f"No recovery step for {recovery['id']}: {recovery['step']}"))

    for prerequisite in bundle.get("prerequisites", []):
        scoped, _, location = _scope(text, prerequisite.get("section"), sections)
        if prerequisite["marker"] not in scoped:
            errors.append(_error("missing_prerequisite", location, "critical", f"Missing prerequisite {prerequisite['id']}"))

    for branch in bundle.get("branches", []):
        scoped, _, location = _scope(text, branch.get("section"), sections)
        if branch["condition"] not in scoped:
            errors.append(_error("missing_branch", location, "critical", f"Missing branch condition {branch['id']}: {branch['condition']}"))
        for marker in branch["required_markers"]:
            if marker not in scoped:
                errors.append(_error("incomplete_branch", location, "critical", f"Branch {branch['id']} is missing: {marker}"))

    return sorted(errors, key=lambda item: (item["location"], item["type"], item["message"]))


def semantic_result(manual: Path, bundle: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    errors = validate_manual(manual.read_text(encoding="utf-8"), bundle, repo_root)
    return {"semantic_valid": not errors, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("manual", type=Path)
    args = parser.parse_args(argv)
    try:
        result = semantic_result(args.manual, load_bundle(args.bundle), args.repo_root)
    except (OSError, ValueError) as exc:
        result = {"semantic_valid": False, "errors": [_error("invalid_input", "input", "critical", str(exc))]}
        print(json.dumps(result, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return int(not result["semantic_valid"])


if __name__ == "__main__":
    raise SystemExit(main())
