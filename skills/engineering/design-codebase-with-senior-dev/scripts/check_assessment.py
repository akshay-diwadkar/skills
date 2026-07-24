#!/usr/bin/env python3
"""Validate a design assessment against the canonical contract v2 and target repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from assessment_contract import (
    Diagnostic,
    load_contract,
    marker,
    section_names,
    validate_receipt,
)

RECORD_RE = re.compile(r"^- (?P<id>(?:TD|T|F|P|C|D|H|A|O|G|V|M|R)-\d+):", re.MULTILINE)

FACT_RE = re.compile(
    r"^- (?P<id>F-\d+): `(?P<path>[^`:]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<observation>.+?)"
    r"(?: \| source: (?P<source>[^|]+))?(?: \| strength: (?P<strength>[^|]+))?(?: \| freshness: (?P<freshness>[^|]+))?$",
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
    r"^- H-\d+: status: assessment-only \| next: (?P<next>finish assessment|plan-with-senior-dev|codebase-issue-auditor|optimize-codebase-with-senior-dev|implement-with-senior-dev)$",
    re.MULTILINE,
)
PATTERN_RE = re.compile(
    r"^- G-\d+: pattern: (?P<pattern>.+?) \| scope: (?P<scope>introduced|removed|relied-upon) \| result: (?P<result>admit|admit-narrowed|retain|remove|reject|defer) \| questions: (?P<questions>.+?) \| evidence: (?P<evidence>.+)$",
    re.MULTILINE,
)
MIGRATION_RE = re.compile(
    r"^- M-\d+: prerequisite: .+? \| changed boundary: .+? \| preserved: (?:C-\d+(?:, C-\d+)*) \| proof: (?:V-\d+(?:, V-\d+)*) \| rollback trigger: .+? \| rollback action: .+? \| cleanup: .+$",
    re.MULTILINE,
)
TECH_DEBT_RE = re.compile(
    r"^- (?P<id>TD-\d+): type: (?P<type>structural|boundary|state-ownership|dependency|migration|operational) \| evidence: (?P<evidence>.+?) \| principal: (?P<principal>.+?) \| interest: (?P<interest>.+?) \| frequency: (?P<frequency>.+?) \| blast-radius: (?P<blast_radius>.+?) \| disposition: (?P<disposition>accept|monitor|contain|repay|retire) \| reason: (?P<reason>.+?) \| repayment-boundary: (?P<repayment_boundary>.+?) \| recurrence-guard: (?P<recurrence_guard>.+?) \| revisit-trigger: (?P<revisit_trigger>.+)$",
    re.MULTILINE,
)
TARGET_DISCOVERY_RE = re.compile(
    r"^- (?P<id>T-\d+): target: (?P<target>.+?) \| evidence: (?P<evidence>.+?) \| pressure: (?P<pressure>.+?) \| affected: (?P<affected>.+?) \| confidence: (?P<confidence>high|medium|low) \| likely-level: (?P<likely_level>L[0-3]) \| blast-radius: (?P<blast_radius>.+?) \| product-intent-required: (?P<product_intent>true|false) \| status: (?P<status>selected|rejected|deferred) \| reason: (?P<reason>.+)$",
    re.MULTILINE,
)
VERIFICATION_RE = re.compile(
    r"^- (?P<id>V-\d+): proves: (?P<proves>[^|]+) \| method: (?P<method>.+?) \| expected: (?P<expected>.+)$",
    re.MULTILINE,
)
ALTERNATIVE_RE = re.compile(
    r"^- (?P<id>O-\d+): level: (?P<level>L[0-3]) \| selected: (?P<selected>yes|no) \| concepts: (?P<concepts>.+?) \| argument-for: (?P<arg_for>.+?) \| argument-against: (?P<arg_against>.+?) \| revisit: (?P<revisit>.+)$",
    re.MULTILINE,
)

PLACEHOLDER_RE = re.compile(r"\bReplace(?: with)?\b|existing_anchor", re.IGNORECASE)
REFERENCE_RE = re.compile(r"\b(?:TD|T|F|P|C|D|A|O|G|V|M|R|H)-\d+\b")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=tuple(load_contract()["levels"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("path", nargs="?", help="Assessment Markdown file; reads stdin when omitted or '-'.")
    parser.add_argument("--require-finalized", action="store_true", help="Require valid SHA-256 validation receipt.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def read_assessment(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _sections(text: str) -> list[tuple[str, int, str]]:
    headings = list(re.finditer(r"^## (?P<name>.+)$", text, re.MULTILINE))
    return [
        (
            match.group("name").strip(),
            text[: match.start()].count("\n") + 1,
            text[match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip(),
        )
        for index, match in enumerate(headings)
    ]


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _validate_shape(text: str, level: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    first = next(((index, line.strip()) for index, line in enumerate(text.splitlines(), start=1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be an H1 title.", first[0] if first else None))
    
    expected_marker = marker(level)
    if expected_marker not in text:
        diagnostics.append(Diagnostic("contract.marker.missing", f"Expected exact marker {expected_marker!r}."))
    for other_level in load_contract()["levels"]:
        if other_level != level and marker(other_level) in text:
            diagnostics.append(Diagnostic("contract.level.mismatch", f"Assessment declares {other_level} but checker expects {level}."))

    parsed = _sections(text)
    names = [name for name, _, _ in parsed]
    expected = section_names(level)
    
    # Allow extra section "Target Discovery Candidates" if autonomous mode
    filtered_names = [n for n in names if n != "Target Discovery Candidates"]
    if filtered_names != expected:
        diagnostics.append(Diagnostic("shape.sections.order", f"H2 sections must be: {', '.join(expected)} (with optional Target Discovery Candidates)."))

    for name, count in Counter(names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times."))
    for name, line_number, body in parsed:
        if not body:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {name!r} is empty.", line_number))
    for match in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("shape.placeholder", f"Unfilled scaffold placeholder {match.group(0)!r}.", _line(text, match.start())))
    return diagnostics


def _validate_decision_summary(text: str, level: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    summary_body = next((body for name, _, body in _sections(text) if name == "Decision Summary"), "")
    if not summary_body:
        return [Diagnostic("summary.missing", "Decision Summary section is required at top of assessment.")]

    lowered = summary_body.casefold()
    if "invocation mode:" not in lowered:
        diagnostics.append(Diagnostic("summary.mode.missing", "Decision Summary must include Invocation mode."))
    if "selected target:" not in lowered:
        diagnostics.append(Diagnostic("summary.target.missing", "Decision Summary must include Selected target."))
    if "selected level:" not in lowered:
        diagnostics.append(Diagnostic("summary.level.missing", "Decision Summary must include Selected level."))
    elif f"selected level: {level.casefold()}" not in lowered:
        diagnostics.append(Diagnostic("summary.level.mismatch", f"Decision Summary selected level must match contract level {level}."))

    if "recommended design:" not in lowered:
        diagnostics.append(Diagnostic("summary.recommendation.missing", "Decision Summary must include Recommended design."))
    if "protected behavior and contracts:" not in lowered:
        diagnostics.append(Diagnostic("summary.contracts.missing", "Decision Summary must include Protected behavior and contracts."))
    if "primary structural pressure:" not in lowered:
        diagnostics.append(Diagnostic("summary.pressure.missing", "Decision Summary must include Primary structural pressure."))
    if "next owner:" not in lowered:
        diagnostics.append(Diagnostic("summary.owner.missing", "Decision Summary must include Next owner."))
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

    # Decision record D-n
    decisions = list(DECISION_RE.finditer(text))
    if len(decisions) != 1:
        diagnostics.append(Diagnostic("decision.format", "Exactly one canonical D-n classification record is required."))
    else:
        d = decisions[0]
        if d.group("level") != level:
            diagnostics.append(Diagnostic("decision.level.mismatch", f"D-n selects {d.group('level')} but contract level is {level}."))
        if not re.search(r"\bF-\d+\b", d.group("because")) or not re.search(r"\bP-\d+\b", d.group("because")):
            diagnostics.append(Diagnostic("decision.evidence.missing", "D-n because field must cite both F-n and P-n."))

    # Alternatives O-n
    alternatives = list(ALTERNATIVE_RE.finditer(text))
    minimum = int(load_contract()["levels"][level]["minimum_alternatives"])
    if len(alternatives) < minimum:
        diagnostics.append(Diagnostic("alternatives.count", f"{level} requires at least {minimum} O-n alternatives; found {len(alternatives)}."))

    selected_alts = [alt for alt in alternatives if alt.group("selected") == "yes"]
    if len(selected_alts) != 1:
        diagnostics.append(Diagnostic("alternatives.selected.count", f"Exactly one O-n alternative must be selected (yes); found {len(selected_alts)}."))
    elif selected_alts[0].group("level") != level:
        diagnostics.append(Diagnostic("alternatives.selected.level_mismatch", f"Selected O-n level {selected_alts[0].group('level')} must match D-n level {level}."))

    # Contracts C-n
    contracts = list(CONTRACT_RE.finditer(text))
    if not contracts:
        diagnostics.append(Diagnostic("contract.record.format", "At least one canonical C-n protected-contract record is required."))
    for contract in contracts:
        status = contract.group("status")
        auth = contract.group("authorization").strip().casefold()
        if status == "authorized-change" and auth in {"none", "unknown", "n/a", "not-applicable"}:
            diagnostics.append(Diagnostic("contract.authorization.missing", "An authorized-change C-n must name explicit authorization.", _line(text, contract.start())))
        elif status == "at-risk":
            if auth in {"none", "unknown", "n/a", "not-applicable"}:
                diagnostics.append(Diagnostic("contract.at_risk.unhandled", "An at-risk C-n must name a resolution owner, path, or blocking status.", _line(text, contract.start())))

    # Tech Debt TD-n
    tech_debts = list(TECH_DEBT_RE.finditer(text))
    for td in tech_debts:
        evidence = td.group("evidence")
        if not re.search(r"\bF-\d+\b", evidence):
            diagnostics.append(Diagnostic("tech_debt.evidence.missing", f"TD record {td.group('id')} must cite at least one F-n record.", _line(text, td.start())))
        disposition = td.group("disposition")
        rec_guard = td.group("recurrence_guard").strip().casefold()
        rev_trigger = td.group("revisit_trigger").strip().casefold()

        if disposition in {"repay", "retire"} and rec_guard in {"none", "n/a", "not-applicable", "unknown"}:
            diagnostics.append(Diagnostic("tech_debt.recurrence_guard.missing", f"TD disposition {disposition} requires a recurrence guard.", _line(text, td.start())))
        if disposition in {"accept", "monitor", "contain"} and rev_trigger in {"none", "n/a", "not-applicable", "unknown"}:
            diagnostics.append(Diagnostic("tech_debt.revisit_trigger.missing", f"TD disposition {disposition} requires a measurable revisit trigger.", _line(text, td.start())))

    # Handoff H-n
    handoff_match = HANDOFF_RE.search(text)
    if not handoff_match:
        diagnostics.append(Diagnostic("handoff.assessment_only", "H-n must keep this skill assessment-only and select one canonical next state."))

    # Target Discovery T-n
    candidates = list(TARGET_DISCOVERY_RE.finditer(text))
    summary_body = next((body for name, _, body in _sections(text) if name == "Decision Summary"), "").casefold()
    mode = "targeted"
    if "invocation mode: autonomous-discovery" in summary_body:
        mode = "autonomous-discovery"
    elif "invocation mode: discovery-only" in summary_body:
        mode = "discovery-only"

    if mode == "targeted":
        selected_targets = [t for t in candidates if t.group("status") == "selected"]
        if selected_targets:
            diagnostics.append(Diagnostic("discovery.targeted.selected_prohibited", "Targeted mode must not contain a selected autonomous target candidate."))
    elif mode == "autonomous-discovery":
        selected_targets = [t for t in candidates if t.group("status") == "selected"]
        if len(selected_targets) != 1:
            diagnostics.append(Diagnostic("discovery.autonomous.selected_count", f"Autonomous mode requires exactly 1 selected T-n candidate; found {len(selected_targets)}."))
        else:
            sel = selected_targets[0]
            if sel.group("product_intent").casefold() == "true":
                diagnostics.append(Diagnostic("discovery.autonomous.product_intent_blocked", "Autonomous selection must fail when product intent is required."))
            if sel.group("confidence").casefold() == "low":
                diagnostics.append(Diagnostic("discovery.autonomous.low_confidence_blocked", "Autonomous selection must fail when candidate confidence is low."))
    elif mode == "discovery-only":
        selected_targets = [t for t in candidates if t.group("status") == "selected"]
        if selected_targets:
            diagnostics.append(Diagnostic("discovery.only.selected_prohibited", "Discovery-only mode must not select a design target."))
        if handoff_match and handoff_match.group("next") != "codebase-issue-auditor":
            diagnostics.append(Diagnostic("discovery.only.handoff_mismatch", "Discovery-only mode must hand off to codebase-issue-auditor."))

    # Verification V-n
    verifications = list(VERIFICATION_RE.finditer(text))
    for v in verifications:
        proves = v.group("proves")
        if not re.search(r"\b(?:TD|T|F|P|C|D|A|O|G|V|M|R|H)-\d+\b", proves):
            diagnostics.append(Diagnostic("verification.proves.missing", f"V-n record {v.group('id')} must cite a target record to prove.", _line(text, v.start())))

    return diagnostics


def _validate_facts(text: str, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    matches = list(FACT_RE.finditer(text))
    if not matches:
        return [Diagnostic("fact.format", "At least one canonical F-n citation is required.")]
    root = repo_root.resolve()

    has_multi_category = False
    categories = set()

    for match in matches:
        path = (root / match.group("path")).resolve()
        source_cat = (match.group("source") or "code").strip().casefold()
        categories.add(source_cat)

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
        result = pattern.group("result")
        if result in {"admit", "admit-narrowed"}:
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
            elif re.search(rf"^- {re.escape(field)}:\s*not-applicable$", operational, re.MULTILINE):
                diagnostics.append(Diagnostic("operational.field.generic_na", f"Operational Semantics field {field!r} marked not-applicable must provide a concrete reason."))

    if level == "L3":
        evolution = next((body for name, _, body in _sections(text) if name == "System Ownership and Evolution"), "").casefold()
        for field in contract["l3_evolution_fields"]:
            if not re.search(rf"^- {re.escape(field)}:", evolution, re.MULTILINE):
                diagnostics.append(Diagnostic("evolution.field.missing", f"System Ownership and Evolution must address {field!r}."))
            elif re.search(rf"^- {re.escape(field)}:\s*(?:not-applicable|n/a)$", evolution, re.MULTILINE):
                diagnostics.append(Diagnostic("evolution.field.na_prohibited", f"L3 System Ownership field {field!r} cannot be satisfied with generic not-applicable."))

        # L3 evidence check: requires multi-category evidence
        facts = list(FACT_RE.finditer(text))
        categories = {match.group("source").strip().casefold() for match in facts if match.group("source")}
        if len(categories) < 3 and len(facts) < 4:
            diagnostics.append(Diagnostic("evidence.l3.categories_insufficient", "L3 classification requires evidence across at least 3 independent categories (code, test, deployment, schema, history, etc.)."))

    return diagnostics


def validate(text: str, level: str, repo_root: Path, *, require_finalized: bool = False) -> list[Diagnostic]:
    diagnostics = [
        *_validate_shape(text, level),
        *_validate_decision_summary(text, level),
        *_validate_records(text, level),
        *_validate_facts(text, repo_root),
        *_validate_level_obligations(text, level),
    ]

    receipt_diags = validate_receipt(text, required=require_finalized)
    diagnostics.extend(receipt_diags)
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diagnostics = validate(
        read_assessment(args.path),
        args.level,
        args.repo_root,
        require_finalized=args.require_finalized,
    )
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
