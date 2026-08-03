#!/usr/bin/env python3
"""Validate one evidence-backed optimization handoff draft."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from optimization_contract import Diagnostic, load_contract, marker, section_names

RECORD_RE = re.compile(r"^- (?P<id>(?:CV|F|B|R|C|V|X|H)-\d+): (?P<body>.+)$", re.MULTILINE)
FACT_RE = re.compile(r"^- (?P<id>F-\d+): `(?P<path>[^`:]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<observation>.+)$", re.MULTILINE)
REFERENCE_RE = re.compile(r"\b(?:CV|F|B|R|C|V|X|H)-\d+\b")
PLACEHOLDER_RE = re.compile(r"\bReplace(?: with)?\b|existing_(?:anchor|symbol)|`path:1`", re.IGNORECASE)


@dataclass(frozen=True)
class Record:
    identifier: str
    fields: dict[str, str]
    line: int


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _sections(text: str) -> list[tuple[str, int, str]]:
    headings = list(re.finditer(r"^## (?P<name>.+)$", text, re.MULTILINE))
    return [
        (match.group("name").strip(), _line(text, match.start()), text[match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip())
        for index, match in enumerate(headings)
    ]


def _fields(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in body.split(" | "):
        if ": " in item:
            key, value = item.split(": ", 1)
            result[key.strip()] = value.strip()
    return result


def _records(text: str) -> dict[str, Record]:
    return {match.group("id"): Record(match.group("id"), _fields(match.group("body")), _line(text, match.start())) for match in RECORD_RE.finditer(text)}


def _values(value: str) -> list[str]:
    return [item.strip().strip("`") for item in value.split(",") if item.strip()]


def _gates(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _values(value):
        name, separator, state = item.partition("=")
        if separator:
            result[name] = state
    return result


def _metadata(text: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}: (?P<value>.+)$", text, re.MULTILINE)
    return match.group("value").strip() if match else ""


def _shape(text: str, scope: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    first = next(((number, line.strip()) for number, line in enumerate(text.splitlines(), 1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be an H1 title.", first[0] if first else None))
    if marker(scope) not in text:
        diagnostics.append(Diagnostic("contract.marker.missing", f"Expected exact marker {marker(scope)!r}."))
    names = [name for name, _, _ in _sections(text)]
    if names != section_names():
        diagnostics.append(Diagnostic("shape.sections.order", f"H2 sections must be exactly: {', '.join(section_names())}."))
    for name, count in Counter(names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times."))
    for name, line_number, body in _sections(text):
        if not body:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {name!r} is empty.", line_number))
    for match in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("shape.placeholder", f"Unfilled scaffold placeholder {match.group(0)!r}.", _line(text, match.start())))
    return diagnostics


def _facts(text: str, repo_root: Path) -> tuple[list[Diagnostic], dict[str, tuple[str, str]]]:
    diagnostics: list[Diagnostic] = []
    facts: dict[str, tuple[str, str]] = {}
    for match in FACT_RE.finditer(text):
        identifier, relative, anchor = match.group("id", "path", "anchor")
        path = (repo_root / relative).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            diagnostics.append(Diagnostic("fact.path.escape", f"{identifier} escapes the repository.", _line(text, match.start())))
            continue
        if not path.is_file():
            diagnostics.append(Diagnostic("fact.path.missing", f"{identifier} path does not exist: {relative}.", _line(text, match.start())))
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        line_number = int(match.group("line"))
        if line_number < 1 or line_number > len(lines) or anchor not in lines[line_number - 1]:
            diagnostics.append(Diagnostic("fact.anchor.missing", f"{identifier} anchor is absent from {relative}:{line_number}.", _line(text, match.start())))
            continue
        facts[identifier] = (relative, anchor)
    return diagnostics, facts


def validate(text: str, execution_path: str, scope: str, stage: str, repo_root: Path, handoff_text: str | None = None) -> list[Diagnostic]:
    if execution_path != "full" or stage != "plan":
        return [Diagnostic("workflow.retired", "Optimization supports only handoff-only full analysis.")]
    if handoff_text is not None:
        return [Diagnostic("handoff.file.unexpected", "A second request artifact is forbidden.")]
    contract = load_contract()
    diagnostics = _shape(text, scope)
    if _metadata(text, "Scope") != scope:
        diagnostics.append(Diagnostic("brief.scope.mismatch", f"Brief must declare Scope: {scope}."))
    if _metadata(text, "Authorization") != "analysis-only":
        diagnostics.append(Diagnostic("authorization.analysis_only", "Optimization handoffs require Authorization: analysis-only."))
    for name in ("Goal", "Success criteria", "Constraints", "Exclusions", "Protected behavior"):
        if not _metadata(text, name):
            diagnostics.append(Diagnostic("brief.field.missing", f"Brief requires {name}."))
    records = _records(text)
    for identifier, count in Counter(match.group("id") for match in RECORD_RE.finditer(text)).items():
        if count > 1:
            diagnostics.append(Diagnostic("record.id.duplicate", f"Record {identifier} is duplicated."))
    for prefix in contract["full"]["base_required_prefixes"]:
        if not any(identifier.startswith(prefix + "-") for identifier in records):
            diagnostics.append(Diagnostic("record.required.missing", f"At least one {prefix}-n record is required."))
    for reference in REFERENCE_RE.findall(text):
        if reference not in records:
            diagnostics.append(Diagnostic("record.reference.missing", f"Reference {reference} has no matching record."))
    fact_diagnostics, facts = _facts(text, repo_root)
    diagnostics.extend(fact_diagnostics)
    handoffs = [record for identifier, record in records.items() if identifier.startswith("H-")]
    if len(handoffs) != 1:
        diagnostics.append(Diagnostic("handoff.count", "Exactly one H-n record is required."))
    else:
        handoff = handoffs[0]
        state = handoff.fields.get("next")
        if state not in contract["handoff_states"]:
            diagnostics.append(Diagnostic("handoff.next.invalid", "H-n has an invalid handoff state.", handoff.line))
        elif state == "plan-ready":
            candidate = records.get(handoff.fields.get("candidate", ""))
            if candidate is None or candidate.fields.get("band") not in {"quick-win", "strategic-win"}:
                diagnostics.append(Diagnostic("handoff.candidate.invalid", "plan-ready requires one winning candidate.", handoff.line))
            elif set(_gates(candidate.fields.get("gates", ""))) != set(contract["promotion_gates"]) or any(value != "yes" for value in _gates(candidate.fields.get("gates", "")).values()):
                diagnostics.append(Diagnostic("handoff.candidate.gates", "plan-ready requires every promotion gate to pass.", candidate.line))
            else:
                cited = set(_values(candidate.fields.get("evidence", "")))
                if not {"F", "B", "R"} <= {item.split("-", 1)[0] for item in cited} or any(item not in records for item in cited):
                    diagnostics.append(Diagnostic("handoff.candidate.evidence", "The winning candidate requires valid F, B, and R evidence.", candidate.line))
                expected_anchors = {f"{facts[item][0]}:{facts[item][1]}" for item in cited if item in facts}
                if set(_values(candidate.fields.get("anchors", ""))) != expected_anchors:
                    diagnostics.append(Diagnostic("handoff.candidate.anchors", "Winning candidate anchors must match cited local facts.", candidate.line))
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=tuple(contract["scopes"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("draft", nargs="?")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    text = sys.stdin.read() if args.draft in {None, "-"} else Path(args.draft).read_text(encoding="utf-8")
    diagnostics = validate(text, "full", args.scope, "plan", args.repo_root)
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [item.to_dict(path=args.draft or "stdin") for item in diagnostics]}, sort_keys=True, separators=(",", ":")))
    elif diagnostics:
        print("\n".join(str(item) for item in diagnostics))
    else:
        print("Optimization handoff validation passed.")
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
