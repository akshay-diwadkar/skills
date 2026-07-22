#!/usr/bin/env python3
"""Check a plan draft for the canonical v3 shape."""

from __future__ import annotations

import argparse
import re
from collections import Counter

from _plan_utils import Diagnostic, read_plan, strip_fenced_code_blocks
from plan_contract import load_contract, section_names
from plan_model import parse_markdown


DEFERRED_PATTERNS = (
    r"\b(?:TBD|TODO|FIXME)\b",
    r"\b(?:decide later|during implementation|as needed|where appropriate|if applicable)\b",
    r"\b(?:update relevant files|make necessary changes|handle edge cases)\b",
)
PERMISSION_PATTERNS = (r"\bshall I proceed\b", r"\bwant me to start\b", r"\blet me know if\b")
GENERIC_TITLES = {"plan", "implementation plan", "change plan", "technical plan"}
CONTRACT_MARKER_RE = re.compile(r"<!--\s*plan-contract:\s*(?P<version>\d+)\s*-->")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(load_contract()["tiers"]), required=True)
    parser.add_argument("path", nargs="?", help="Plan markdown file. Reads stdin when omitted or set to '-'.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--warn", action="store_true")
    return parser.parse_args()


def line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def validate(text: str, tier: str) -> list[Diagnostic]:
    contract = load_contract()
    tier_contract = contract["tiers"][tier]
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    first = next(((index, line.strip()) for index, line in enumerate(lines, start=1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be one H1 title", first[0] if first else None))
    elif (
        first[1][2:].strip().casefold() in GENERIC_TITLES
        or len(re.findall(r"[A-Za-z0-9]+", first[1][2:])) < 4
    ):
        diagnostics.append(Diagnostic(
            "shape.title.not_descriptive",
            "Title must describe the concrete outcome, not merely label the document as a plan",
            first[0],
        ))

    markers = list(CONTRACT_MARKER_RE.finditer(text))
    if len(markers) != 1 or markers[0].group("version") != str(contract["contract_version"]):
        found = ", ".join(match.group("version") for match in markers) or "none"
        diagnostics.append(Diagnostic(
            "contract.version.unsupported",
            f"Plan must declare exactly one v3 contract marker; found {found}. Regenerate with scripts/scaffold_plan.py.",
        ))

    document = parse_markdown(text)
    diagnostics.extend(document.diagnostics)
    h2_names = [section.name for section in document.sections if section.level == 2]
    expected = section_names(tier)
    for name in expected:
        if name not in h2_names:
            diagnostics.append(Diagnostic("shape.section.missing", f"Missing required v3 section: {name}"))
    for name, count in Counter(h2_names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times"))
    for section in document.sections:
        if section.level == 2 and not section.has_content:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {section.name!r} is empty", section.line))

    count = line_count(strip_fenced_code_blocks(text))
    if count < tier_contract["minimum_non_empty_lines"]:
        diagnostics.append(Diagnostic("shape.line_count.under", f"{tier} plan has {count} non-empty lines; expected at least {tier_contract['minimum_non_empty_lines']}"))
    if count > tier_contract["advisory_max_non_empty_lines"]:
        diagnostics.append(Diagnostic(
            "shape.line_count.repetition_risk",
            f"{tier} plan has {count} non-empty lines; review for repetition above advisory {tier_contract['advisory_max_non_empty_lines']}",
            is_warning=True,
        ))

    scan = strip_fenced_code_blocks(text)
    for line_number, line in enumerate(scan.splitlines(), start=1):
        for pattern in DEFERRED_PATTERNS:
            if match := re.search(pattern, line, re.IGNORECASE):
                diagnostics.append(Diagnostic("shape.deferred_decision", f"Deferred or vague language: {match.group(0)!r}", line_number))
        if re.search(r"\bReplace with\b|replace-with-command|existing_anchor", line, re.IGNORECASE):
            diagnostics.append(Diagnostic("shape.scaffold.placeholder", "Unfilled scaffold placeholder remains", line_number))
    for line_number, line in list(enumerate(scan.splitlines(), start=1))[-8:]:
        for pattern in PERMISSION_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                diagnostics.append(Diagnostic("shape.permission_to_proceed", "Plan must not end by asking permission to proceed", line_number))
    return diagnostics


def main() -> int:
    args = parse_args()
    text = read_plan(args.path)
    diagnostics = validate(text, args.tier)
    if diagnostics:
        print("Plan shape check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Plan shape check passed.")
    errors = [item for item in diagnostics if not item.is_warning]
    warnings = [item for item in diagnostics if item.is_warning]
    return 1 if errors or (warnings and not args.warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
