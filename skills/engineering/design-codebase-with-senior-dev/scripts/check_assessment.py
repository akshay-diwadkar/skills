#!/usr/bin/env python3
"""Validate a design assessment against the canonical contract and repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from assessment_contract import Diagnostic, load_contract, marker, section_names

RECORD_RE = re.compile(r"^- (?P<id>[FPCDHAOGVMR]-\d+):", re.MULTILINE)
FACT_RE = re.compile(
    r"^- (?P<id>F-\d+): `(?P<path>[^`:]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<observation>.+)$",
    re.MULTILINE,
)
DECISION_RE = re.compile(
    r"^- D-\d+: level: (?P<level>L[0-3]) \| selected: (?P<selected>.+?) \| because: (?P<because>.+?) \| rejected: (?P<rejected>.+)$",
    re.MULTILINE,
)
CONTRACT_RE = re.compile(
    r"^- C-\d+: status: (?P<status>preserved|authorized-change|at-risk) \| contract: (?P<contract>.+?) \| authorization: (?P<authorization>.+)$",
    re.MULTILINE,
)
HANDOFF_RE = re.compile(
    r"^- H-\d+: status: assessment-only \| next: (?P<next>finish assessment|plan-with-senior-dev|implement-with-senior-dev)$",
    re.MULTILINE,
)
PATTERN_RE = re.compile(
    r"^- G-\d+: pattern: (?P<pattern>.+?) \| scope: (?P<scope>introduced|removed|relied-upon) \| result: (?P<result>admit|reject) \| questions: (?P<questions>.+?) \| evidence: (?P<evidence>.+)$",
    re.MULTILINE,
)
MIGRATION_RE = re.compile(
    r"^- M-\d+: prerequisite: .+? \| changed boundary: .+? \| preserved: C-\d+(?:, C-\d+)* \| proof: V-\d+(?:, V-\d+)* \| rollback trigger: .+? \| rollback action: .+? \| cleanup: .+$",
    re.MULTILINE,
)
PLACEHOLDER_RE = re.compile(r"\bReplace(?: with)?\b|existing_anchor", re.IGNORECASE)
REFERENCE_RE = re.compile(r"\b(?:F|P|C|D|A|O|G|V|M|R|H)-\d+\b")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=tuple(load_contract()["levels"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("path", nargs="?", help="Assessment Markdown file; reads stdin when omitted or '-'.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def read_assessment(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _sections(text: str) -> list[tuple[str, int, str]]:
    headings = list(re.finditer(r"^## (?P<name>.+)$", text, re.MULTILINE))
    return [
        (match.group("name").strip(), text[: match.start()].count("\n") + 1, text[match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip())
        for index, match in enumerate(headings)
    ]


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _validate_shape(text: str, level: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    first = next(((index, line.strip()) for index, line in enumerate(text.splitlines(), start=1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be an H1 title.", first[0] if first else None))
    if marker(level) not in text:
        diagnostics.append(Diagnostic("contract.marker.missing", f"Expected exact marker {marker(level)!r}."))
    for other_level in load_contract()["levels"]:
        if other_level != level and marker(other_level) in text:
            diagnostics.append(Diagnostic("contract.level.mismatch", f"Assessment declares {other_level} but checker expects {level}."))

    parsed = _sections(text)
    names = [name for name, _, _ in parsed]
    expected = section_names(level)
    if names != expected:
        diagnostics.append(Diagnostic("shape.sections.order", f"H2 sections must be exactly: {', '.join(expected)}."))
    for name, count in Counter(names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times."))
    for name, line_number, body in parsed:
        if not body:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {name!r} is empty.", line_number))
    for match in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("shape.placeholder", f"Unfilled scaffold placeholder {match.group(0)!r}.", _line(text, match.start())))
    return diagnostics


def _validate_records(text: str, level: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    identifiers = [match.group("id") for match in RECORD_RE.finditer(text)]
    known = set(identifiers)
    for identifier, count in Counter(identifiers).items():
        if count > 1:
            diagnostics.append(Diagnostic("record.id.duplicate", f"Record {identifier} appears {count} times."))
    required_prefixes = {"F", "P", "C", "D", "H", "A", "O", "V", "R"}
    for prefix in required_prefixes:
        if not any(identifier.startswith(f"{prefix}-") for identifier in identifiers):
            diagnostics.append(Diagnostic("record.required.missing", f"At least one {prefix}-n record is required."))
    for reference in REFERENCE_RE.findall(text):
        if reference not in known:
            diagnostics.append(Diagnostic("record.reference.missing", f"Reference {reference} has no matching record."))

    decisions = list(DECISION_RE.finditer(text))
    if len(decisions) != 1:
        diagnostics.append(Diagnostic("decision.format", "Exactly one canonical D-n classification record is required."))
    elif decisions[0].group("level") != level:
        diagnostics.append(Diagnostic("decision.level.mismatch", f"D-n selects {decisions[0].group('level')} but contract level is {level}."))
    elif not re.search(r"\bF-\d+\b", decisions[0].group("because")) or not re.search(r"\bP-\d+\b", decisions[0].group("because")):
        diagnostics.append(Diagnostic("decision.evidence.missing", "D-n because field must cite both F-n and P-n."))

    alternatives = len(re.findall(r"^- O-\d+:", text, re.MULTILINE))
    minimum = int(load_contract()["levels"][level]["minimum_alternatives"])
    if alternatives < minimum:
        diagnostics.append(Diagnostic("alternatives.count", f"{level} requires at least {minimum} O-n alternatives; found {alternatives}."))

    contracts = list(CONTRACT_RE.finditer(text))
    if not contracts:
        diagnostics.append(Diagnostic("contract.record.format", "At least one canonical C-n protected-contract record is required."))
    for contract in contracts:
        if contract.group("status") == "authorized-change" and contract.group("authorization").strip().casefold() in {"none", "unknown", "n/a", "not-applicable"}:
            diagnostics.append(Diagnostic("contract.authorization.missing", "An authorized-change C-n must name explicit authorization.", _line(text, contract.start())))
    if not HANDOFF_RE.search(text):
        diagnostics.append(Diagnostic("handoff.assessment_only", "H-n must keep this skill assessment-only and select one canonical next state."))
    return diagnostics


def _validate_facts(text: str, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    matches = list(FACT_RE.finditer(text))
    if not matches:
        return [Diagnostic("fact.format", "At least one canonical F-n citation is required.")]
    root = repo_root.resolve()
    for match in matches:
        path = (root / match.group("path")).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            diagnostics.append(Diagnostic("fact.path.outside_repo", f"Citation path escapes repository: {match.group('path')}.", _line(text, match.start())))
            continue
        if not path.is_file():
            diagnostics.append(Diagnostic("fact.path.missing", f"Cited file does not exist: {match.group('path')}.", _line(text, match.start())))
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        line_number = int(match.group("line"))
        if line_number < 1 or line_number > len(lines):
            diagnostics.append(Diagnostic("fact.line.missing", f"Cited line {line_number} does not exist in {match.group('path')}.", _line(text, match.start())))
            continue
        if match.group("anchor") not in lines[line_number - 1]:
            diagnostics.append(Diagnostic("fact.anchor.missing", f"Anchor {match.group('anchor')!r} is not on {match.group('path')}:{line_number}.", _line(text, match.start())))
    return diagnostics


def _validate_level_obligations(text: str, level: str) -> list[Diagnostic]:
    contract = load_contract()
    level_contract = contract["levels"][level]
    diagnostics: list[Diagnostic] = []
    patterns = list(PATTERN_RE.finditer(text))
    if level_contract["requires_pattern_gate"] and not patterns:
        diagnostics.append(Diagnostic("pattern.required", f"{level} requires at least one canonical G-n pattern decision."))
    hard_questions = {int(number) for number in contract["hard_pattern_questions"]}
    for pattern in patterns:
        answers = {int(number): answer for number, answer in re.findall(r"Q(\d+)=(yes|no|unknown)", pattern.group("questions"))}
        if set(answers) != set(range(1, 15)):
            diagnostics.append(Diagnostic("pattern.questions.incomplete", "G-n must answer Q1-Q14 exactly once.", _line(text, pattern.start())))
        if pattern.group("result") == "admit":
            failed = sorted(number for number in hard_questions if answers.get(number) != "yes")
            if failed:
                diagnostics.append(Diagnostic("pattern.hard_gate.failed", f"Admitted pattern fails or omits hard questions: {failed}.", _line(text, pattern.start())))

    if level_contract["requires_migration"] and not MIGRATION_RE.search(text):
        diagnostics.append(Diagnostic("migration.format", f"{level} requires a canonical M-n slice with proof and executable rollback."))
    if level_contract["requires_operational_semantics"]:
        operational = next((body for name, _, body in _sections(text) if name == "Operational Semantics"), "").casefold()
        for field in contract["operational_fields"]:
            if not re.search(rf"^- {re.escape(field)}:", operational, re.MULTILINE):
                diagnostics.append(Diagnostic("operational.field.missing", f"Operational Semantics must address {field!r}."))
    if level == "L3":
        evolution = next((body for name, _, body in _sections(text) if name == "System Ownership and Evolution"), "").casefold()
        for field in contract["l3_evolution_fields"]:
            if not re.search(rf"^- {re.escape(field)}:", evolution, re.MULTILINE):
                diagnostics.append(Diagnostic("evolution.field.missing", f"System Ownership and Evolution must address {field!r}."))
    return diagnostics


def validate(text: str, level: str, repo_root: Path) -> list[Diagnostic]:
    return [
        *_validate_shape(text, level),
        *_validate_records(text, level),
        *_validate_facts(text, repo_root),
        *_validate_level_obligations(text, level),
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diagnostics = validate(read_assessment(args.path), args.level, args.repo_root)
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [item.to_dict() for item in diagnostics]}, indent=2))
    elif diagnostics:
        print("Assessment check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Assessment check passed.")
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
