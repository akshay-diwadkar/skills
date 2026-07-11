#!/usr/bin/env python3
"""Check a plan draft against the plan-quality rubric."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent directory to path so we can import _plan_utils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plan_utils import Diagnostic, read_plan, strip_fenced_code_blocks


SECTION_ALIASES = {
    "Success Criteria": ("Success Criteria", "Outcome and Scope"),
    "Current State": ("Current State", "Evidence", "Evidence and Decisions"),
    "Scope": ("Scope", "Outcome and Scope"),
    "Approach": ("Approach", "Evidence and Decisions"),
    "Changes": ("Changes", "Implementation Specification"),
    "Test Strategy": ("Test Strategy", "Test/Verification", "Verification", "Verification and Risks"),
    "Rollback Plan": ("Rollback Plan", "Verification and Risks", "Durable Rollback"),
    "Change Propagation": ("Change Propagation", "Change Propagation Map", "Propagation Map", "Traceability and Constraints"),
    "Constraint Verification": ("Constraint Verification", "Constraints", "Traceability and Constraints"),
    "Devil's Advocate": ("Devil's Advocate", "Attack Findings", "Verification and Risks", "Risk Register"),
    "Logic Specification": ("Logic Specification", "Pseudo-code", "Pseudocode", "Implementation Specification"),
    "Compatibility": ("Compatibility",),
    "Migration": ("Migration", "Migration and Rollout"),
    "Risk": ("Risk", "Risk Register", "Verification and Risks"),
    "Pre-Mortem Findings": ("Pre-Mortem Findings", "Verification and Risks"),
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

MEASURABLE_VERBS = (
    "returns", "return", "displays", "display", "rejects", "reject",
    "emits", "emit", "logs", "log", "creates", "create", "deletes", "delete",
    "responds", "respond", "shows", "show", "verifies", "verify", "asserts", "assert",
)

BLAST_RADIUS_WORDS = (
    "blast radius",
    "caller",
    "callers",
    "consumer",
    "consumers",
    "importer",
    "importers",
    "route",
    "routes",
    "job",
    "jobs",
    "worker",
    "workers",
    "webhook",
    "webhooks",
    "subscriber",
    "subscribers",
    "client",
    "clients",
    "shared",
    "config",
    "schema",
    "schemas",
    "contract",
    "contracts",
    "downstream",
    "affected",
)

INVARIANT_WORDS = (
    "invariant",
    "invariants",
    "preserve",
    "preserves",
    "unchanged",
    "do not change",
    "does not change",
    "keep",
    "keeps",
    "remain",
    "remains",
)

SIDE_EFFECT_WORDS = (
    "side effect",
    "side effects",
    "persistent",
    "persistence",
    "persisted",
    "database",
    "data",
    "schema",
    "migration",
    "network",
    "external",
    "filesystem",
    "file system",
    "cache",
    "queue",
    "job",
    "worker",
    "webhook",
    "notification",
    "email",
    "billing",
    "charge",
    "idempotent",
    "idempotency",
    "no persistent",
    "no external",
    "no data",
    "no filesystem",
    "no durable",
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
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="Separate warnings from errors. If set, warnings do not cause exit code 1.",
    )
    return parser.parse_args()


def parse_sections(text: str) -> tuple[dict[str, Section], list[Diagnostic]]:
    scan_text = strip_fenced_code_blocks(text)
    lines = scan_text.splitlines()
    headings: list[tuple[str, int, int]] = []
    
    diagnostics: list[Diagnostic] = []
    seen_headings: dict[str, int] = {}
    
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            name = re.sub(r"\s*\([^)]*\)\s*$", "", match.group(1)).strip()
            line_number = index + 1
            if name in seen_headings:
                diagnostics.append(Diagnostic(
                    code="rubric.section.duplicate",
                    message=f"Duplicate section {name!r} parsed in rubric checker",
                    line=line_number
                ))
            else:
                seen_headings[name] = line_number
            headings.append((name, line_number, index))

    sections: dict[str, Section] = {}
    for position, (name, line_number, line_index) in enumerate(headings):
        end_index = headings[position + 1][2] if position + 1 < len(headings) else len(lines)
        body = "\n".join(lines[line_index + 1 : end_index]).strip()
        # Avoid overwriting with duplicates if we want to preserve the first one
        if name not in sections:
            sections[name] = Section(name=name, line=line_number, body=body)
            
    return sections, diagnostics


def extract_fenced_code_blocks(text: str) -> list[tuple[str, str, int]]:
    blocks: list[tuple[str, str, int]] = []
    pattern = re.compile(r"^```([A-Za-z0-9_-]*)\s*$([\s\S]*?)^```\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        lang = match.group(1).casefold()
        body = match.group(2)
        line = text[: match.start()].count("\n") + 1
        blocks.append((lang, body, line))
    return blocks


def section(sections: dict[str, Section], name: str) -> Section | None:
    for alias in SECTION_ALIASES.get(name, (name,)):
        for actual_name, section_obj in sections.items():
            if actual_name.casefold() == alias.casefold():
                return section_obj
    return None


def fail(code: str, message: str, section_obj: Section | None = None, is_warning: bool = False) -> Diagnostic:
    line = section_obj.line if section_obj is not None else None
    return Diagnostic(code=code, message=message, line=line, is_warning=is_warning)


def has_repo_evidence(body: str, tier: str) -> bool:
    if tier == "tiny":
        if re.search(r"[\w./\\-]+\.\w+:\d+", body):
            return True
        if re.search(r"`[^`]*(?:/|\\|\.ts|\.tsx|\.js|\.jsx|\.py|\.go|\.rs|\.java|\.md|\.json|\.ya?ml)[^`]*`", body):
            return True
    else:
        # Standard and high-risk require line numbers in citations
        if re.search(r"[\w./\\-]+\.\w+:\d+", body):
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


def has_word_from(body: str, words: tuple[str, ...]) -> bool:
    lowered = body.casefold()
    return any(word in lowered for word in words)


def has_blast_radius(body: str) -> bool:
    return has_word_from(body, BLAST_RADIUS_WORDS)


def has_invariant(body: str) -> bool:
    return has_word_from(body, INVARIANT_WORDS)


def references_existing_pattern(body: str) -> bool:
    return bool(
        re.search(
            r"\b(existing|current|local|nearby|analogous|precedent|pattern|exception|follow)\b",
            body,
            flags=re.IGNORECASE,
        )
    )


def is_ordered(body: str) -> bool:
    return bool(re.search(r"^\s*(?:\d+\.|[-*]\s+(?:(?:First|Then|Next|Finally)\b|CH-\d+\s*:))", body, flags=re.MULTILINE | re.IGNORECASE))


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


def has_side_effect_boundary(*bodies: str) -> bool:
    return has_word_from("\n".join(bodies), SIDE_EFFECT_WORDS)


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
    return bool(re.search(r"\bP[012]\b", body))


def has_unresolved_p0(body: str) -> bool:
    return bool(re.search(r"\bP0\s*:\s*(?:unresolved|TBD|ask later|open|unknown)", body, flags=re.IGNORECASE))


def p0_p1_risks_have_actions(body: str) -> bool:
    risk_lines = [
        line.strip()
        for line in body.splitlines()
        if re.search(r"\bP[01]\b", line)
    ]
    if not risk_lines:
        return False
    return all(re.search(r"\bAction\s*:", line, flags=re.IGNORECASE) for line in risk_lines)


def pre_mortem_findings_are_actionable(section_obj: Section | None) -> bool:
    if section_obj is None or not section_obj.body.strip():
        return True
    lines = [line.strip() for line in section_obj.body.splitlines() if line.strip()]
    finding_lines = [line for line in lines if re.search(r"\bP[012]\b", line)]
    if not finding_lines:
        return False
    return all("Action:" in line for line in finding_lines)


def has_propagation_map(body: str) -> bool:
    has_arrow = bool(re.search(r"(?:->|→)", body))
    has_file_ref = bool(re.search(r"[\w./\\-]+\.\w+:\d+|`[^`]*(?:/|\\|\.\w+)[^`]*`", body))
    has_update_required = bool(re.search(r"\bupdate required\s*:\s*(?:yes|no)\b", body, flags=re.IGNORECASE))
    return has_arrow and has_file_ref and has_update_required


def has_constraint_classification(body: str) -> bool:
    has_classification = bool(re.search(r"\b(preserved|modified|at[- ]risk)\b", body, flags=re.IGNORECASE))
    has_evidence = bool(re.search(r"\bevidence\b|[\w./\\-]+\.\w+:\d+|`[^`]+`", body, flags=re.IGNORECASE))
    return has_classification and has_evidence


def count_attack_findings(body: str) -> int:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    count = 0
    for line in lines:
        if re.match(r"^(?:[-*]|\d+\.)\s+", line) and re.search(
            r"\b(P[012]|scenario|failure|attack|fix|accepted risk)\b",
            line,
            flags=re.IGNORECASE,
        ):
            count += 1
    if count:
        return count
    return len(re.findall(r"\bP[012]\b", body))


def has_function_like_pseudocode(text: str) -> bool:
    for lang, body, _ in extract_fenced_code_blocks(text):
        if lang not in {"", "text", "pseudo", "pseudocode", "python", "py", "typescript", "ts", "javascript", "js"}:
            continue
        if re.search(
            r"\bfunction\s+\w+\s*\([^)]*:\s*[^)]*\)\s*:\s*[\w<>\[\]|.]+",
            body,
        ):
            return True
        if re.search(r"\bdef\s+\w+\s*\([^)]*:\s*[^)]*\)\s*->\s*[\w.\[\]|]+", body):
            return True
        if re.search(
            r"^\s*\w+\s*\([^)]*:\s*[^)]*\)\s*(?:->|:)\s*[\w<>\[\]|.]+",
            body,
            flags=re.MULTILINE,
        ):
            return True
    return False


def has_test_assertion_specificity(body: str) -> bool:
    patterns = (
        r"\bassert(?:s|ion)?\b",
        r"\bexpect\s*\(",
        r"\binput\b[\s\S]{0,160}\boutput\b",
        r"\boutput\b[\s\S]{0,160}\binput\b",
        r"\bgiven\b[\s\S]{0,120}\breturns?\b",
        r"`[^`]+`\s*(?:->|=>|\breturns?\b)\s*`?[^`\n]+",
    )
    return any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in patterns)


def validate_attack_findings(sections: dict[str, Section]) -> list[Diagnostic]:
    attack = section(sections, "Devil's Advocate")
    if attack is None:
        return [Diagnostic(
            code="rubric.devils_advocate.missing",
            message="Missing Devil's Advocate or Attack Findings section",
        )]
    if attack.name == "Verification and Risks":
        if re.search(r"\bR-\d+\s+P[012]\b", attack.body):
            return []
        if re.search(r"\bno material (?:risk|finding|failure)\b", attack.body, flags=re.IGNORECASE):
            return []
        return [fail(
            "rubric.devils_advocate.depth",
            "Verification and Risks must contain a concrete R-n finding or evidenced no-material-risk result",
            attack,
        )]
    if count_attack_findings(attack.body) < 3 and not re.search(
        r"fewer than three|no material (?:risk|finding|failure)",
        attack.body,
        flags=re.IGNORECASE,
    ):
        return [fail(
            "rubric.devils_advocate.depth",
            "Devil's Advocate must contain at least 3 concrete findings",
            attack,
        )]
    return []


def validate_standard_reasoning_sections(sections: dict[str, Section], full_text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    propagation = section(sections, "Change Propagation")
    constraints = section(sections, "Constraint Verification")

    if propagation is None:
        diagnostics.append(Diagnostic(
            code="rubric.propagation.missing",
            message="Missing Change Propagation or Propagation Map section",
        ))
    elif not has_propagation_map(propagation.body):
        diagnostics.append(fail(
            "rubric.propagation.completeness",
            "Propagation map must include an arrow, file references, and update required yes/no entries",
            propagation,
        ))

    if constraints is None:
        diagnostics.append(Diagnostic(
            code="rubric.constraints.missing",
            message="Missing Constraint Verification or Constraints section",
        ))
    elif not has_constraint_classification(constraints.body):
        diagnostics.append(fail(
            "rubric.constraints.evidence",
            "Constraint Verification must classify constraints as preserved, modified, or at risk with evidence",
            constraints,
        ))

    if not has_function_like_pseudocode(full_text):
        diagnostics.append(Diagnostic(
            code="rubric.pseudocode.quality",
            message="Pseudo-code must include function-like signatures with typed parameters and return types",
        ))

    return diagnostics


def require_section(sections: dict[str, Section], diagnostics: list[Diagnostic], name: str) -> Section | None:
    found = section(sections, name)
    if found is None:
        diagnostics.append(Diagnostic(code="rubric.section.missing", message=f"Missing section {name!r}"))
    return found


def validate_tiny(sections: dict[str, Section]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    current = require_section(sections, diagnostics, "Current State")
    change = require_section(sections, diagnostics, "Change")
    tests = require_section(sections, diagnostics, "Test Strategy")
    assumptions = require_section(sections, diagnostics, "Assumptions")
    diagnostics.extend(validate_attack_findings(sections))

    if current and not has_repo_evidence(current.body, "tiny"):
        diagnostics.append(fail("rubric.current_state.evidence", "Current State must cite repo evidence or justify N/A", current))
    if change and (not change.body.strip() or has_generic_work(change.body)):
        diagnostics.append(fail("rubric.change.concrete", "Change must name concrete behavior, not generic work", change))
    if tests:
        if not has_command_or_manual_check(tests.body):
            diagnostics.append(fail("rubric.test_strategy.command", "Test/Verification must include an exact command or explicit manual check", tests))
        if not has_expected_result(tests.body):
            diagnostics.append(fail("rubric.test_strategy.expected_result", "Test/Verification must include expected passing result", tests))
        if not has_test_assertion_specificity(tests.body):
            diagnostics.append(fail("rubric.test_strategy.assertions", "Test/Verification must include exact assertions or input/output pairs", tests))
    if assumptions and not assumptions.body.strip():
        diagnostics.append(fail("rubric.assumptions.non_empty", "Assumptions must not be empty", assumptions))

    return diagnostics


def validate_standard(sections: dict[str, Section], full_text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    current = require_section(sections, diagnostics, "Current State")
    scope = require_section(sections, diagnostics, "Scope")
    approach = require_section(sections, diagnostics, "Approach")
    changes = require_section(sections, diagnostics, "Changes")
    tests = require_section(sections, diagnostics, "Test Strategy")
    rollback = require_section(sections, diagnostics, "Rollback Plan")
    assumptions = require_section(sections, diagnostics, "Assumptions")
    diagnostics.extend(validate_attack_findings(sections))
    diagnostics.extend(validate_standard_reasoning_sections(sections, full_text))

    if current and not has_repo_evidence(current.body, "standard"):
        diagnostics.append(fail("rubric.current_state.evidence", "Current State must cite repo evidence with file:line or justify N/A", current))
    if scope and not has_scope_boundaries(scope.body):
        diagnostics.append(fail("rubric.scope.boundaries", "Scope must include in-scope and out-of-scope or unchanged behavior", scope))
    if scope and not has_invariant(scope.body):
        diagnostics.append(fail("rubric.scope.invariants", "Scope must name invariants or unchanged behavior that the plan preserves", scope))
    if scope and not has_blast_radius(scope.body):
        diagnostics.append(fail("rubric.scope.blast_radius", "Scope must name the blast radius: affected callers, clients, jobs, config, contracts, or downstream surfaces", scope))
    if approach and not references_existing_pattern(approach.body):
        diagnostics.append(fail("rubric.approach.pattern", "Approach must reference an existing pattern, local precedent, or explicit exception", approach))
    if changes and not is_ordered(changes.body):
        diagnostics.append(fail("rubric.changes.order", "Changes must be dependency-ordered with numbered steps or ordered bullets", changes))
    if tests:
        if not has_scenario_language(tests.body):
            diagnostics.append(fail("rubric.test_strategy.scenarios", "Test Strategy must name scenarios or cases", tests))
        if not has_command_or_manual_check(tests.body):
            diagnostics.append(fail("rubric.test_strategy.command", "Test Strategy must include exact commands or explicit manual checks", tests))
        if not has_expected_result(tests.body):
            diagnostics.append(fail("rubric.test_strategy.expected_result", "Test Strategy must include expected passing result", tests))
        if not has_test_assertion_specificity(tests.body):
            diagnostics.append(fail("rubric.test_strategy.assertions", "Test Strategy must include exact assertions or input/output pairs", tests))
    if rollback and not has_concrete_rollback(rollback.body):
        diagnostics.append(fail("rubric.rollback.concrete", "Rollback Plan must state concrete steps or trivial rollback reason", rollback))
    failure_modes = section(sections, "Failure Modes")
    rollback_body = rollback.body if rollback else ""
    failure_body = failure_modes.body if failure_modes else ""
    if not has_side_effect_boundary(rollback_body, failure_body):
        diagnostics.append(fail(
            "rubric.side_effects.boundary",
            "Failure Modes or Rollback Plan must state side-effect handling or explicitly say there are no persistent, external, data, or filesystem side effects",
            rollback or failure_modes,
        ))
    if assumptions and not distinguishes_assumptions(assumptions.body):
        diagnostics.append(fail("rubric.assumptions.classified", "Assumptions must distinguish low-impact, accepted, or blocking assumptions", assumptions))
    if has_risk_language(full_text) and not has_mitigation(full_text):
        diagnostics.append(fail("rubric.risk.mitigation", "Risk language requires mitigation or Pre-Mortem Findings"))

    # New validation checks:
    
    # 1. Interface-specification check
    # Check if Changes or Approach mentions API/schema/type/event/command
    has_interface_keywords = False
    for sec_obj in (changes, approach):
        if sec_obj and any(kw in sec_obj.body.lower() for kw in ("api", "schema", "type", "event", "command")):
            has_interface_keywords = True
            break
    if has_interface_keywords:
        # Check if the full text has any code block defining a shape (e.g. ```typescript, ```json, etc.)
        # Simply checking if there is a code block at all in the full text (we stripped fenced blocks for analysis,
        # so let's check the original raw text)
        if not re.search(r"```", full_text):
            diagnostics.append(fail(
                "rubric.interface.specification",
                "Changes or Approach mentions interface (API/schema/type/event/command) but no code block defining its shape was found"
            ))

    # 2. Doc Updates awareness (Warning)
    has_doc_signals = bool(re.search(r"\b(glossary|context\.md|adr|adrs|context-map\.md)\b", full_text, flags=re.IGNORECASE))
    if has_doc_signals and "Doc Updates" not in sections:
        diagnostics.append(fail(
            "rubric.docs.missing_section",
            "Plan contains domain terminology or documentation references, but missing 'Doc Updates' section",
            is_warning=True
        ))

    # 3. Failure-mode check (Warning)
    has_failure_keywords = bool(re.search(r"\b(error|failure|exception|fail|timeout|fallback|retry)\b", full_text, flags=re.IGNORECASE))
    if "Failure Modes" not in sections and "Verification and Risks" not in sections and not has_failure_keywords:
        diagnostics.append(fail(
            "rubric.failure_modes.missing",
            "Missing 'Failure Modes' section and no error/failure scenarios found in plan body",
            is_warning=True
        ))

    # 4. Success criteria specificity check (Warning)
    success_criteria = section(sections, "Success Criteria")
    if success_criteria:
        has_measurable = any(verb in success_criteria.body.lower() for verb in MEASURABLE_VERBS)
        if not has_measurable:
            diagnostics.append(fail(
                "rubric.success_criteria.vague",
                "Success Criteria does not use measurable verbs (e.g., returns, displays, rejects, emits)",
                success_criteria,
                is_warning=True
            ))

    # 5. Tracer Bullet validation
    tracer_bullet = section(sections, "Tracer Bullet")
    if tracer_bullet:
        # Check if tracer bullet has repo evidence (standard/high-risk level requiring file:line or specific path)
        if not has_repo_evidence(tracer_bullet.body, "standard") and not re.search(r"`[^`]+`", tracer_bullet.body):
            diagnostics.append(fail(
                "rubric.tracer_bullet.vague",
                "Tracer Bullet section does not reference specific files, endpoints, or commands",
                tracer_bullet
            ))

    # 6. Warn on missing pre-mortem (Warning)
    pre_mortem = section(sections, "Pre-Mortem Findings")
    if not pre_mortem and not has_risk_language(full_text):
        diagnostics.append(fail(
            "rubric.pre_mortem.missing",
            "No pre-mortem findings or risk language found in Standard plan",
            is_warning=True
        ))

    return diagnostics


def validate_high_risk(sections: dict[str, Section], full_text: str) -> list[Diagnostic]:
    diagnostics = validate_standard(sections, full_text)
    compatibility = require_section(sections, diagnostics, "Compatibility")
    migration = require_section(sections, diagnostics, "Migration")
    risk = require_section(sections, diagnostics, "Risk")
    pre_mortem = section(sections, "Pre-Mortem Findings")

    if compatibility and not compatibility_is_specific(compatibility.body):
        diagnostics.append(fail("rubric.compatibility.specific", "Compatibility must cover old/new clients, data, or contracts", compatibility))
    if migration and not migration_is_specific(migration.body):
        diagnostics.append(fail("rubric.migration.specific", "Migration must include validation, dry-run, backfill, dual-read, or rollback detail", migration))
    if risk:
        if not has_risk_tiers(risk.body):
            diagnostics.append(fail("rubric.risk.tiers", "Risk must use P0, P1, and P2 severity labels where applicable", risk))
        if has_unresolved_p0(risk.body):
            diagnostics.append(fail("rubric.risk.unresolved_p0", "Risk must not leave P0 unresolved", risk))
        risk_mitigation_body = risk.body
        if pre_mortem:
            risk_mitigation_body = f"{risk_mitigation_body}\n{pre_mortem.body}"
        if not p0_p1_risks_have_actions(risk_mitigation_body):
            diagnostics.append(fail("rubric.risk.p0_p1_actions", "Every P0 and P1 risk must include Action: mitigation", risk))
    if not pre_mortem_findings_are_actionable(pre_mortem):
        diagnostics.append(fail("rubric.pre_mortem.action", "Pre-Mortem Findings must include tiered findings with Action:", pre_mortem))

    return diagnostics


def validate(text: str, tier: str) -> list[Diagnostic]:
    sections, parse_diags = parse_sections(text)
    
    if tier == "tiny":
        diags = validate_tiny(sections)
    elif tier == "standard":
        diags = validate_standard(sections, text) # pass original text to check code blocks
    else:
        diags = validate_high_risk(sections, text)

    return parse_diags + diags


def main() -> int:
    args = parse_args()
    try:
        text = read_plan(args.path)
    except Exception as e:
        print(f"Error reading plan: {e}", file=sys.stderr)
        return 1

    diagnostics = validate(text, args.tier)

    errors = [d for d in diagnostics if not d.is_warning]
    warnings = [d for d in diagnostics if d.is_warning]

    if args.format == "json":
        import json
        output = {
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "passed": len(errors) == 0 and (args.warn or len(warnings) == 0),
        }
        print(json.dumps(output, indent=2))
    else:
        if diagnostics:
            print("Plan rubric check findings:")
            for d in diagnostics:
                print(f"- {d}")
        else:
            print("Plan rubric check passed.")

    if errors:
        return 1
    if warnings and not args.warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
