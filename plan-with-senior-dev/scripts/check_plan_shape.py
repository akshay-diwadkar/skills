#!/usr/bin/env python3
"""Check a plan draft for tier-appropriate shape and length."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TIERS = {
    "tiny": {
        "min_lines": 8,
        "max_lines": 50,
        "sections": [
            "Goal",
            "Current State",
            "Change",
            "Test/Verification",
            "Assumptions",
        ],
    },
    "standard": {
        "min_lines": 20,
        "max_lines": 90,
        "sections": [
            "Goal",
            "Success Criteria",
            "Current State",
            "Scope",
            "Approach",
            "Changes",
            "Test Strategy",
            "Rollback Plan",
            "Assumptions",
        ],
        "one_of": [
            ("Tracer Bullet", "Failure Modes"),
        ],
    },
    "high-risk": {
        "min_lines": 50,
        "max_lines": 180,
        "sections": [
            "Goal",
            "Success Criteria",
            "Current State",
            "Scope",
            "Approach",
            "Changes",
            "Test Strategy",
            "Rollback Plan",
            "Assumptions",
            "Compatibility",
            "Migration",
            "Risk",
        ],
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
    ],
}


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
    return parser.parse_args()


def read_plan(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def headings(text: str) -> set[str]:
    found: set[str] = set()
    for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE):
        heading = re.sub(r"\s*\([^)]*\)\s*$", "", match.group(1)).strip()
        found.add(heading)
    return found


def line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def first_non_empty_line(text: str) -> tuple[int, str] | None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            return line_number, line.strip()
    return None


def title_failures(text: str) -> list[str]:
    first_line = first_non_empty_line(text)
    if first_line is None:
        return ["missing title: plan is empty"]

    line_number, line = first_line
    if not line.startswith("# "):
        return [f"missing H1 title on first non-empty line {line_number}: {line!r}"]
    if line.startswith("##"):
        return [f"title must be exactly one H1 heading on line {line_number}: {line!r}"]

    title = line[2:].strip()
    if not title:
        return [f"title is empty on line {line_number}"]

    normalized = re.sub(r"\s+", " ", title.casefold()).strip()
    if normalized in GENERIC_TITLES:
        return [f"title on line {line_number} is too generic: {title!r}"]

    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", title)
    if len(words) < 4 or len(words) > 12:
        return [
            f"title on line {line_number} has {len(words)} words; expected 4 to 12"
        ]

    if not re.search(r"\b(add|fix|remove|replace|migrate|split|merge|rename|update|introduce|enforce|validate|support|prevent|restore|document|wire|route)\b", title, flags=re.IGNORECASE):
        return [
            f"title on line {line_number} should name a concrete behavior or change: {title!r}"
        ]

    return []


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


def uncertainty_failures(text: str) -> list[str]:
    failures: list[str] = []
    scan_text = strip_fenced_code_blocks(text)
    for line_number, line in enumerate(scan_text.splitlines(), start=1):
        for rule_name, patterns in UNCERTAINTY_RULES.items():
            for pattern in patterns:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    failures.append(
                        f"{rule_name} on line {line_number}: {match.group(0)!r}"
                    )
                    break
    return failures


def validate(text: str, tier: str) -> list[str]:
    rules = TIERS[tier]
    failures: list[str] = []
    count = line_count(text)
    if count < rules["min_lines"]:
        failures.append(
            f"{tier} plan has {count} non-empty lines; expected at least {rules['min_lines']}"
        )
    if count > rules["max_lines"]:
        failures.append(
            f"{tier} plan has {count} non-empty lines; expected at most {rules['max_lines']}"
        )

    failures.extend(title_failures(text))

    found = headings(text)
    for section in rules["sections"]:
        if not any(heading == section or heading.startswith(section + " ") for heading in found):
            failures.append(f"missing required section: {section}")

    for group in rules.get("one_of", []):
        if not any(
            any(heading == option or heading.startswith(option + " ") for heading in found)
            for option in group
        ):
            failures.append(f"missing one of required sections: {', '.join(group)}")

    failures.extend(uncertainty_failures(text))

    if tier in {"standard", "high-risk"} and not re.search(r"`[^`]+`|[\w./\\-]+:\d+", text):
        failures.append("no obvious command, code path, or file:line citation found")

    return failures


def main() -> int:
    args = parse_args()
    text = read_plan(args.path)
    failures = validate(text, args.tier)
    if failures:
        print("Plan shape check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Plan shape check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
