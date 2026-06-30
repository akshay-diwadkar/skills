#!/usr/bin/env python3
"""Check a plan draft against the plan-quality rubric."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SECTION_ALIASES = {
    "Test Strategy": ("Test Strategy", "Test/Verification"),
}

EXPECTED_WORDS = (
    "expect",
    "expected",
    "passes",
    "pass",
    "passing",
    "returns",
    "shows",
    "confirms",
    "verifies",
    "with no",
    "zero",
)


@dataclass(frozen=True)
class Section:
    name: str
    line: int
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("tiny", "standard", "high-risk"),
        required=True,
        help="Plan complexity tier to validate against.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Plan markdown file. Reads stdin when omitted or set to '-'.",
    )
    return parser.parse_args()


def read_plan(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def strip_fenced_code_blocks(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    in_fence = False
    for line in lines:
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            output.append("")
            continue
        output.append("" if in_fence else line)
    return "\n".join(output)


def parse_sections(text: str) -> dict[str, Section]:
    scan_text = strip_fenced_code_blocks(text)
    lines = scan_text.splitlines()
    headings: list[tuple[str, int, int]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            name = re.sub(r"\s*\([^)]*\)\s*$", "", match.group(1)).strip()
            headings.append((name, index + 1, index))

    sections: dict[str, Section] = {}
    for position, (name, line_number, line_index) in enumerate(headings):
        end_index = headings[position + 1][2] if position + 1 < len(headings) else len(lines)
        body = "\n".join(lines[line_index + 1 : end_index]).strip()
        sections[name] = Section(name=name, line=line_number, body=body)
    return sections


def section(sections: dict[str, Section], name: str) -> Section | None:
    for alias in SECTION_ALIASES.get(name, (name,)):
        if alias in sections:
            return sections[alias]
    return None


def fail(code: str, message: str, section_obj: Section | None = None) -> str:
    if section_obj is None:
        return f"{code}: {message}"
    return f"{code} on line {section_obj.line}: {message}"


def has_repo_evidence(body: str) -> bool:
    if re.search(r"[\w./\\-]+\.\w+:\d+", body):
        return True
    if re.search(r"`[^`]*(?:/|\\|\.ts|\.tsx|\.js|\.jsx|\.py|\.go|\.rs|\.java|\.md|\.json|\.ya?ml)[^`]*`", body):
        return True
    if re.search(r"\bN/A\b.*\b(low-risk|not applicable|no repo change|no code change|single-file|docs-only)\b", body, flags=re.IGNORECASE):
        return True
    return False


def has_command_or_manual_check(body: str) -> bool:
    if re.search(r"`[^`]+`", body):
        return True
    return bool(re.search(r"\b(manual check|manually verify|inspect|open|click|run)\b", body, flags=re.IGNORECASE))


def has_expected_result(body: str) -> bool:
    return any(word in body.casefold() for word in EXPECTED_WORDS)


def has_generic_work(body: str) -> bool:
    return bool(
        re.search(
            r"\b(update relevant files|make necessary changes|handle edge cases|wire up|clean up|integrate as needed)\b",
            body,
            flags=re.IGNORECASE,
        )
    )


def has_scope_boundaries(body: str) -> bool:
    has_in_scope = bool(re.search(r"\b(in scope|change|include|update|touch|modify)\b", body, flags=re.IGNORECASE))
    has_out_scope = bool(re.search(r"\b(out of scope|unchanged|do not|does not|keep .* unchanged|exclude)\b", body, flags=re.IGNORECASE))
    return has_in_scope and has_out_scope


def references_existing_pattern(body: str) -> bool:
    return bool(
        re.search(
            r"\b(existing|current|local|nearby|analogous|precedent|pattern|exception|follow)\b",
            body,
            flags=re.IGNORECASE,
        )
    )


def is_ordered(body: str) -> bool:
    return bool(re.search(r"^\s*(?:\d+\.|[-*]\s+(?:First|Then|Next|Finally)\b)", body, flags=re.MULTILINE | re.IGNORECASE))


def has_scenario_language(body: str) -> bool:
    return bool(re.search(r"\b(scenario|case|when|given|happy path|failure|missing|invalid|empty|legacy|rollback)\b", body, flags=re.IGNORECASE))


def has_concrete_rollback(body: str) -> bool:
    return bool(
        re.search(
            r"\b(revert|rollback|roll back|disable|flag|restore|backfill|down migration|trivial|no persistent|no data|no external)\b",
            body,
            flags=re.IGNORECASE,
        )
    )


def distinguishes_assumptions(body: str) -> bool:
    if not body.strip():
        return False
    return bool(re.search(r"\b(low-impact|blocking|non-blocking|accepted|N/A|no .* needed|assume|assumption)\b", body, flags=re.IGNORECASE))


def has_risk_language(text: str) -> bool:
    return bool(re.search(r"\b(risk|P0|P1|P2|pre-mortem|migration|rollback|compatibility)\b", text, flags=re.IGNORECASE))


def has_mitigation(text: str) -> bool:
    return bool(re.search(r"\b(mitigat|fallback|rollback|test|verify|validate|monitor|flag|pre-mortem findings)\b", text, flags=re.IGNORECASE))


def compatibility_is_specific(body: str) -> bool:
    return bool(re.search(r"\b(old|new|legacy|client|contract|data|schema|API|backward|compatible|read|write)\b", body, flags=re.IGNORECASE))


def migration_is_specific(body: str) -> bool:
    return bool(re.search(r"\b(validate|dry-run|dry run|backfill|dual-read|rollback|batch|checkpoint|migration|reversible|down)\b", body, flags=re.IGNORECASE))


def has_risk_tiers(body: str) -> bool:
    return all(re.search(rf"\b{tier}\b", body) for tier in ("P0", "P1", "P2"))


def has_unresolved_p0(body: str) -> bool:
    return bool(re.search(r"\bP0\s*:\s*(?:unresolved|TBD|ask later|open|unknown)", body, flags=re.IGNORECASE))


def pre_mortem_findings_are_actionable(section_obj: Section | None) -> bool:
    if section_obj is None or not section_obj.body.strip():
        return True
    lines = [line.strip() for line in section_obj.body.splitlines() if line.strip()]
    finding_lines = [line for line in lines if re.search(r"\bP[012]\b", line)]
    if not finding_lines:
        return False
    return all("Action:" in line for line in finding_lines)


def require_section(sections: dict[str, Section], failures: list[str], name: str) -> Section | None:
    found = section(sections, name)
    if found is None:
        failures.append(f"rubric.section.missing: Missing section {name!r}")
    return found


def validate_tiny(sections: dict[str, Section]) -> list[str]:
    failures: list[str] = []
    current = require_section(sections, failures, "Current State")
    change = require_section(sections, failures, "Change")
    tests = require_section(sections, failures, "Test Strategy")
    assumptions = require_section(sections, failures, "Assumptions")

    if current and not has_repo_evidence(current.body):
        failures.append(fail("rubric.current_state.evidence", "Current State must cite repo evidence or justify N/A", current))
    if change and (not change.body.strip() or has_generic_work(change.body)):
        failures.append(fail("rubric.change.concrete", "Change must name concrete behavior, not generic work", change))
    if tests:
        if not has_command_or_manual_check(tests.body):
            failures.append(fail("rubric.test_strategy.command", "Test/Verification must include an exact command or explicit manual check", tests))
        if not has_expected_result(tests.body):
            failures.append(fail("rubric.test_strategy.expected_result", "Test/Verification must include expected passing result", tests))
    if assumptions and not assumptions.body.strip():
        failures.append(fail("rubric.assumptions.non_empty", "Assumptions must not be empty", assumptions))

    return failures


def validate_standard(sections: dict[str, Section], full_text: str) -> list[str]:
    failures: list[str] = []
    current = require_section(sections, failures, "Current State")
    scope = require_section(sections, failures, "Scope")
    approach = require_section(sections, failures, "Approach")
    changes = require_section(sections, failures, "Changes")
    tests = require_section(sections, failures, "Test Strategy")
    rollback = require_section(sections, failures, "Rollback Plan")
    assumptions = require_section(sections, failures, "Assumptions")

    if current and not has_repo_evidence(current.body):
        failures.append(fail("rubric.current_state.evidence", "Current State must cite repo evidence or justify N/A", current))
    if scope and not has_scope_boundaries(scope.body):
        failures.append(fail("rubric.scope.boundaries", "Scope must include in-scope and out-of-scope or unchanged behavior", scope))
    if approach and not references_existing_pattern(approach.body):
        failures.append(fail("rubric.approach.pattern", "Approach must reference an existing pattern, local precedent, or explicit exception", approach))
    if changes and not is_ordered(changes.body):
        failures.append(fail("rubric.changes.order", "Changes must be dependency-ordered with numbered steps or ordered bullets", changes))
    if tests:
        if not has_scenario_language(tests.body):
            failures.append(fail("rubric.test_strategy.scenarios", "Test Strategy must name scenarios or cases", tests))
        if not has_command_or_manual_check(tests.body):
            failures.append(fail("rubric.test_strategy.command", "Test Strategy must include exact commands or explicit manual checks", tests))
        if not has_expected_result(tests.body):
            failures.append(fail("rubric.test_strategy.expected_result", "Test Strategy must include expected passing result", tests))
    if rollback and not has_concrete_rollback(rollback.body):
        failures.append(fail("rubric.rollback.concrete", "Rollback Plan must state concrete steps or trivial rollback reason", rollback))
    if assumptions and not distinguishes_assumptions(assumptions.body):
        failures.append(fail("rubric.assumptions.classified", "Assumptions must distinguish low-impact, accepted, or blocking assumptions", assumptions))
    if has_risk_language(full_text) and not has_mitigation(full_text):
        failures.append("rubric.risk.mitigation: Risk language requires mitigation or Pre-Mortem Findings")

    return failures


def validate_high_risk(sections: dict[str, Section], full_text: str) -> list[str]:
    failures = validate_standard(sections, full_text)
    compatibility = require_section(sections, failures, "Compatibility")
    migration = require_section(sections, failures, "Migration")
    risk = require_section(sections, failures, "Risk")
    pre_mortem = section(sections, "Pre-Mortem Findings")

    if compatibility and not compatibility_is_specific(compatibility.body):
        failures.append(fail("rubric.compatibility.specific", "Compatibility must cover old/new clients, data, or contracts", compatibility))
    if migration and not migration_is_specific(migration.body):
        failures.append(fail("rubric.migration.specific", "Migration must include validation, dry-run, backfill, dual-read, or rollback detail", migration))
    if risk:
        if not has_risk_tiers(risk.body):
            failures.append(fail("rubric.risk.tiers", "Risk must use P0, P1, and P2 language", risk))
        if has_unresolved_p0(risk.body):
            failures.append(fail("rubric.risk.unresolved_p0", "Risk must not leave P0 unresolved", risk))
    if not pre_mortem_findings_are_actionable(pre_mortem):
        failures.append(fail("rubric.pre_mortem.action", "Pre-Mortem Findings must include tiered findings with Action:", pre_mortem))

    return failures


def validate(text: str, tier: str) -> list[str]:
    clean_text = strip_fenced_code_blocks(text)
    sections = parse_sections(clean_text)
    if tier == "tiny":
        return validate_tiny(sections)
    if tier == "standard":
        return validate_standard(sections, clean_text)
    return validate_high_risk(sections, clean_text)


def main() -> int:
    args = parse_args()
    text = read_plan(args.path)
    failures = validate(text, args.tier)
    if failures:
        print("Rubric check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Rubric check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
