#!/usr/bin/env python3
"""Check a plan draft for tier-appropriate shape and length."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path so we can import _plan_utils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plan_utils import Diagnostic, read_plan, strip_fenced_code_blocks


TIERS: dict[str, dict[str, Any]] = {
    "tiny": {
        "min_lines": 8,
        "max_lines": 60,
        "sections": [
            "Goal",
            "Current State",
            "Change",
            "Test/Verification",
            "Assumptions",
        ],
    },
    "standard": {
        "min_lines": 30,
        "max_lines": 140,
        "sections": [
            "Goal",
            "Success Criteria",
            "Current State",
            "Scope",
            "Reasoning Summary",
            "Approach",
            "Changes",
            "Logic Specification",
            "Test Strategy",
            "Rollback Plan",
            "Assumptions",
        ],
        "optional_warn": [
            "Doc Updates",
            "Tracer Bullet",
            "Failure Modes",
        ],
    },
    "high-risk": {
        "min_lines": 60,
        "max_lines": 220,
        "sections": [
            "Goal",
            "Success Criteria",
            "Current State",
            "Scope",
            "Reasoning Summary",
            "Approach",
            "Changes",
            "Logic Specification",
            "Test Strategy",
            "Rollback Plan",
            "Assumptions",
            "Compatibility",
            "Migration",
            "Risk",
            "Pre-Mortem Findings",
        ],
        "optional_warn": [
            "Doc Updates",
        ]
    },
}

GENERIC_TITLES = {
    "plan",
    "implementation plan",
    "refactor plan",
    "feature plan",
    "bug fix plan",
    "proposed plan",
}

UNCERTAINTY_RULES = {
    "deferred_decision": [
        r"\bdecide later\b",
        r"\bduring implementation\b",
        r"\bleave it to the implementer\b",
        r"\bchoose the appropriate\b",
        r"\bfinalize later\b",
    ],
    "placeholder": [
        r"\bTBD\b",
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\bplaceholder\b",
        r"\bfill in\b",
    ],
    "vague_work": [
        r"\bupdate relevant files\b",
        r"\bmake necessary changes\b",
        r"\bhandle edge cases\b",
        r"\bwire up\b",
        r"\bclean up\b",
        r"\bintegrate as needed\b",
    ],
    "weak_verification": [
        r"^\s*(?:[-*]\s*)?run tests\.?\s*$",
        r"\bensure tests pass\b",
        r"\btest thoroughly\b",
        r"^\s*(?:[-*]\s*)?manual QA\.?\s*$",
    ],
    "underspecified_interface": [
        r"\b(?:API details|schema details|response shape|contract details|types)\b.*\b(?:later|TBD|as needed|during implementation)\b",
        r"\b(?:later|TBD|as needed|during implementation)\b.*\b(?:API details|schema details|response shape|contract details|types)\b",
    ],
    "soft_commitment": [
        r"\bmight want to\b",
        r"\bcould potentially\b",
        r"\bconsider implementing\b",
        r"\bmaybe\b",
        r"\bprobably\b",
        r"\bif needed\b",
        r"\bwhere appropriate\b",
        r"\bas appropriate\b",
        r"\bwhen suitable\b",
        r"\bif applicable\b",
        r"\bwhere relevant\b",
        r"\boptionally\b",
    ],
}

OVER_ABSTRACTION_PATTERNS = [
    r"\bcreate a provider\b",
    r"\badd a factory\b",
    r"\bintroduce an adapter\b",
    r"\bbuild a registry\b",
]

PERMISSION_TO_PROCEED_PATTERNS = [
    r"\bshall I proceed\b",
    r"\bready to implement\b",
    r"\bwant me to start\b",
    r"\blet me know if\b",
    r"\bawaiting your approval\b",
]


def extract_fenced_code_blocks(text: str) -> list[tuple[str, str, int]]:
    blocks: list[tuple[str, str, int]] = []
    pattern = re.compile(r"^```([A-Za-z0-9_-]*)\s*$([\s\S]*?)^```\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        lang = match.group(1).casefold()
        body = match.group(2)
        line = text[: match.start()].count("\n") + 1
        blocks.append((lang, body, line))
    return blocks


def has_pseudocode_block(text: str) -> bool:
    pseudo_langs = {"pseudo", "pseudocode"}
    for lang, body, _ in extract_fenced_code_blocks(text):
        if lang in pseudo_langs:
            return True
        if re.search(r"\b(if|else|elif|for|while|return|throw|raise)\b", body, flags=re.IGNORECASE) and re.search(
            r"\b(function|def|returns?|->|:)\b", body,
            flags=re.IGNORECASE,
        ):
            return True
    return False


def has_any_section(found_names: set[str], alternatives: tuple[str, ...]) -> bool:
    for heading in found_names:
        for alternative in alternatives:
            if heading == alternative or heading.startswith(alternative + " "):
                return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=sorted(TIERS),
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


def line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def first_non_empty_line(text: str) -> tuple[int, str] | None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            return line_number, line.strip()
    return None


def title_failures(text: str) -> list[Diagnostic]:
    first_line = first_non_empty_line(text)
    if first_line is None:
        return [Diagnostic(code="shape.title.empty", message="missing title: plan is empty")]

    line_number, line = first_line
    if not line.startswith("# "):
        return [Diagnostic(code="shape.title.not_h1", message=f"missing H1 title on first non-empty line: {line!r}", line=line_number)]
    if line.startswith("##"):
        return [Diagnostic(code="shape.title.multiple_h1", message=f"title must be exactly one H1 heading: {line!r}", line=line_number)]

    title = line[2:].strip()
    if not title:
        return [Diagnostic(code="shape.title.empty", message="title is empty", line=line_number)]

    normalized = re.sub(r"\s+", " ", title.casefold()).strip()
    if normalized in GENERIC_TITLES:
        return [Diagnostic(code="shape.title.generic", message=f"title is too generic: {title!r}", line=line_number)]

    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", title)
    if len(words) < 4 or len(words) > 12:
        return [Diagnostic(
            code="shape.title.word_count",
            message=f"title has {len(words)} words; expected 4 to 12",
            line=line_number
        )]

    if not re.search(
        r"\b(add|fix|remove|replace|migrate|split|merge|rename|update|introduce|enforce|validate|support|prevent|restore|document|wire|route|refactor|extract|deprecate|implement|enable|disable|create|delete|handle|configure|optimize|normalize|decouple|consolidate|restrict)\b",
        title,
        flags=re.IGNORECASE
    ):
        return [Diagnostic(
            code="shape.title.no_verb",
            message=f"title should name a concrete behavior or change with an action verb: {title!r}",
            line=line_number
        )]

    return []


def validate(text: str, tier: str) -> list[Diagnostic]:
    rules = TIERS[tier]
    diagnostics: list[Diagnostic] = []

    # 1. Line count check
    count = line_count(text)
    if count < rules["min_lines"]:
        diagnostics.append(Diagnostic(
            code="shape.line_count.under",
            message=f"{tier} plan has {count} non-empty lines; expected at least {rules['min_lines']}"
        ))
    if count > rules["max_lines"]:
        diagnostics.append(Diagnostic(
            code="shape.line_count.over",
            message=f"{tier} plan has {count} non-empty lines; expected at most {rules['max_lines']}"
        ))

    # 2. Title check
    diagnostics.extend(title_failures(text))

    # Stripped text for heading detection (ignores headings inside fenced code blocks)
    scan_lines = strip_fenced_code_blocks(text).splitlines()

    # 3. Duplicate heading check
    found_headings: list[tuple[str, int]] = []
    lines = text.splitlines()
    for index, line in enumerate(scan_lines, start=1):
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            heading = re.sub(r"\s*\([^)]*\)\s*$", "", match.group(1)).strip()
            found_headings.append((heading, index))

    heading_counts: dict[str, int] = {}
    for heading, _ in found_headings:
        heading_counts[heading] = heading_counts.get(heading, 0) + 1

    for heading, count_val in heading_counts.items():
        if count_val > 1:
            first_line = next(line_num for h, line_num in found_headings if h == heading)
            diagnostics.append(Diagnostic(
                code="shape.heading.duplicate",
                message=f"Duplicate heading found: {heading!r} appears {count_val} times",
                line=first_line
            ))

    # 4 & 5. Required and optional sections
    found_names = {h for h, _ in found_headings}

    # Required sections
    for section in rules["sections"]:
        if not any(heading == section or heading.startswith(section + " ") for heading in found_names):
            diagnostics.append(Diagnostic(
                code="shape.section.missing_required",
                message=f"Missing required section: {section}"
            ))

    # New structural sections introduced by the six-gate planning workflow.
    if not has_any_section(found_names, ("Devil's Advocate", "Attack Findings")):
        diagnostics.append(Diagnostic(
            code="shape.section.missing_devils_advocate",
            message="Missing required section: Devil's Advocate or Attack Findings"
        ))

    if tier in {"standard", "high-risk"}:
        if not has_any_section(found_names, ("Change Propagation", "Propagation Map")):
            diagnostics.append(Diagnostic(
                code="shape.section.missing_change_propagation",
                message="Missing required section: Change Propagation or Propagation Map"
            ))
        if not has_any_section(found_names, ("Constraint Verification", "Constraints")):
            diagnostics.append(Diagnostic(
                code="shape.section.missing_constraints",
                message="Missing required section: Constraint Verification or Constraints"
            ))
        if not has_pseudocode_block(text):
            diagnostics.append(Diagnostic(
                code="shape.pseudocode.missing",
                message="Standard and High-risk plans must include a fenced pseudo-code block"
            ))

    # Optional warnings sections
    for section in rules.get("optional_warn", []):
        if not any(heading == section or heading.startswith(section + " ") for heading in found_names):
            diagnostics.append(Diagnostic(
                code="shape.section.missing_optional",
                message=f"Missing optional section: {section}",
                is_warning=True
            ))

    # 6. Empty section check
    heading_indices: list[int] = []
    for i, line in enumerate(scan_lines):
        if re.match(r"^#{1,6}\s+", line):
            heading_indices.append(i)

    for idx, start_idx in enumerate(heading_indices):
        end_idx = heading_indices[idx + 1] if idx + 1 < len(heading_indices) else len(lines)
        content = "\n".join(lines[start_idx + 1 : end_idx]).strip()
        clean_content = strip_fenced_code_blocks(content)
        non_empty_lines = [line for line in clean_content.splitlines() if line.strip()]

        if not non_empty_lines:
            heading_text = lines[start_idx].strip()
            heading_match = re.match(r"^#+", heading_text)
            assert heading_match is not None
            heading_level = len(heading_match.group(0))
            heading_name = re.sub(r"^#{1,6}\s+", "", heading_text)
            heading_name_clean = re.sub(r"\s*\([^)]*\)\s*$", "", heading_name).strip()

            is_required = heading_name_clean in rules["sections"] or any(heading_name_clean.startswith(s + " ") for s in rules["sections"])
            is_optional = heading_name_clean in rules.get("optional_warn", []) or any(heading_name_clean.startswith(s + " ") for s in rules.get("optional_warn", []))

            if heading_level == 2 or is_required or is_optional:
                is_warn = is_optional and not is_required
                diagnostics.append(Diagnostic(
                    code="shape.section.empty",
                    message=f"Section {heading_name_clean!r} is empty (has no body content)",
                    line=start_idx + 1,
                    is_warning=is_warn
                ))

    # 7. Uncertainty checks
    scan_text = strip_fenced_code_blocks(text)
    for line_number, line in enumerate(scan_text.splitlines(), start=1):
        for rule_name, patterns in UNCERTAINTY_RULES.items():
            for pattern in patterns:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    diagnostics.append(Diagnostic(
                        code=f"shape.uncertainty.{rule_name}",
                        message=f"Uncertainty pattern {match.group(0)!r} matches rule {rule_name}",
                        line=line_number
                    ))
                    break

    # Over-abstraction check
    has_pattern_ref = bool(re.search(
        r"\b(existing|current|local|nearby|analogous|precedent|pattern|exception|follow)\b",
        text,
        flags=re.IGNORECASE
    ))
    if not has_pattern_ref:
        for line_number, line in enumerate(scan_text.splitlines(), start=1):
            for pattern in OVER_ABSTRACTION_PATTERNS:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    diagnostics.append(Diagnostic(
                        code="shape.uncertainty.over_abstraction",
                        message=f"Over-abstraction pattern {match.group(0)!r} found without existing pattern reference",
                        line=line_number
                    ))
                    break

    # 8. Permission to proceed check (last 5 non-empty lines)
    non_empty_scan_lines = [(line_num, line) for line_num, line in enumerate(scan_text.splitlines(), start=1) if line.strip()]
    last_5_lines = non_empty_scan_lines[-5:] if len(non_empty_scan_lines) >= 5 else non_empty_scan_lines
    for line_num, line in last_5_lines:
        for pattern in PERMISSION_TO_PROCEED_PATTERNS:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                diagnostics.append(Diagnostic(
                    code="shape.uncertainty.permission_to_proceed",
                    message=f"Plan asks for permission to proceed: {match.group(0)!r} near end of document",
                    line=line_num
                ))
                break

    # 9. Evidence check
    if tier in {"standard", "high-risk"} and not re.search(r"`[^`]+`|[\w./\\-]+:\d+", text):
        diagnostics.append(Diagnostic(
            code="shape.evidence.missing",
            message="No obvious command, code path, or file:line citation found"
        ))

    return diagnostics


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
            print("Plan shape check findings:")
            for d in diagnostics:
                print(f"- {d}")
        else:
            print("Plan shape check passed.")

    if errors:
        return 1
    if warnings and not args.warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
