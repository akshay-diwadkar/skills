#!/usr/bin/env python3
"""Deterministically route an engineering request without executing a workflow."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

Skill = Literal[
    "map-codebase",
    "design-codebase",
    "plan-change",
    "implement-plan",
    "audit-codebase",
    "optimize-codebase",
    "scope-issue",
    "diagram-codebase",
    "manualize",
    "raise-issue",
]
Confidence = Literal["high", "medium", "low"]
NextAction = Literal["answer_directly", "invoke_prerequisite", "invoke_primary_skill"]

SKILLS: Final[tuple[Skill, ...]] = (
    "map-codebase",
    "design-codebase",
    "plan-change",
    "implement-plan",
    "audit-codebase",
    "optimize-codebase",
    "scope-issue",
    "diagram-codebase",
    "manualize",
    "raise-issue",
)
ALLOWED_ACTIONS: Final[tuple[str, ...]] = (
    "read_request",
    "read_repository_facts",
    "emit_routing_decision",
)
FORBIDDEN_ACTIONS: Final[tuple[str, ...]] = (
    "plan",
    "edit_source",
    "publish_issues",
    "commit",
    "push",
    "create_pull_request",
    "execute_selected_workflow",
)

IMPLEMENT_WORDS: Final[tuple[str, ...]] = (
    "apply",
    "build",
    "change",
    "edit",
    "fix",
    "implement",
    "migrate",
    "patch",
    "refactor",
    "rename",
    "update",
)
PLAN_WORDS: Final[tuple[str, ...]] = (
    "plan",
    "implementation plan",
    "change plan",
)
ORIENTATION_PHRASES: Final[tuple[str, ...]] = (
    "map the codebase",
    "map this repository",
    "understand this repository",
    "understand the codebase",
    "unfamiliar repository",
    "unfamiliar codebase",
    "where is",
    "where does",
    "which file",
    "which symbol",
    "which component owns",
    "implementation ownership",
    "locate the owner",
)
MANUAL_NOUNS: Final[tuple[str, ...]] = (
    "manual",
    "procedure",
    "runbook",
    "notice",
    "error message",
    "installation guide",
    "technical guide",
    "reference documentation",
)
DIAGRAM_PHRASES: Final[tuple[str, ...]] = (
    "diagram",
    "architecture picture",
    "workflow visualization",
    "visualize the architecture",
    "visualise the architecture",
)
DESIGN_PHRASES: Final[tuple[str, ...]] = (
    "boundary",
    "boundaries",
    "dependency direction",
    "state ownership",
    "abstraction",
    "subsystem design",
    "structural design",
    "redesign",
    "architecture decision",
    "consolidate modules",
    "consolidate components",
)
OPTIMIZATION_NOUNS: Final[tuple[str, ...]] = (
    "bottleneck",
    "latency",
    "throughput",
    "performance",
    "build time",
    "ci time",
    "slow build",
    "slow test",
    "dependency bloat",
    "developer experience",
    "maintainability workflow",
)
OPTIMIZATION_VERBS: Final[tuple[str, ...]] = (
    "benchmark",
    "improve",
    "investigate",
    "measure",
    "optimize",
    "optimise",
    "reduce",
    "speed up",
)
AUDIT_PHRASES: Final[tuple[str, ...]] = (
    "audit",
    "review the codebase",
    "review the repository",
    "find bugs",
    "find risks",
    "hunt for",
    "security risks",
    "test gaps",
    "unknown risks",
    "code quality problems",
    "maintainability problems",
)
ISSUE_PHRASES: Final[tuple[str, ...]] = (
    "github issue",
    "open issues",
    "issue inventory",
    "backlog triage",
    "triage issue",
    "scope issue",
)
RAISE_ISSUE_PHRASES: Final[tuple[str, ...]] = ("audit-handoff", "raise issue", "publish issues", "create issues")


@dataclass(frozen=True)
class RepositoryFacts:
    repository_available: bool = False
    approved_plan_available: bool = False
    issue_context_available: bool = False
    repository_navigation_inadequate: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    primary_skill: Skill | None
    prerequisites: tuple[Skill, ...]
    follow_up: tuple[Skill, ...]
    reason: str
    confidence: Confidence
    next_action: NextAction
    allowed_actions: tuple[str, ...] = ALLOWED_ACTIONS
    forbidden_actions: tuple[str, ...] = FORBIDDEN_ACTIONS

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_skill": self.primary_skill,
            "prerequisites": list(self.prerequisites),
            "follow_up": list(self.follow_up),
            "reason": self.reason,
            "confidence": self.confidence,
            "next_action": self.next_action,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
        }


def normalize_request(request: str) -> str:
    """Return a stable matching representation."""
    normalized = unicodedata.normalize("NFKC", request).casefold()
    normalized = normalized.replace("→", " -> ")
    return re.sub(r"\s+", " ", normalized).strip()


def contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text) is not None


def named_skills(text: str) -> list[Skill]:
    """Return explicitly named skills in textual order."""
    matches: list[tuple[int, Skill]] = []
    for skill in SKILLS:
        variants = (skill, skill.replace("-", " "))
        positions = [text.find(variant) for variant in variants if text.find(variant) >= 0]
        if positions:
            matches.append((min(positions), skill))
    return [skill for _, skill in sorted(matches)]


def unique_skills(skills: tuple[Skill, ...]) -> tuple[Skill, ...]:
    return tuple(dict.fromkeys(skills))


def make_decision(
    primary: Skill | None,
    reason: str,
    *,
    prerequisites: tuple[Skill, ...] = (),
    follow_up: tuple[Skill, ...] = (),
    confidence: Confidence = "high",
) -> RoutingDecision:
    prerequisites = unique_skills(tuple(skill for skill in prerequisites if skill != primary))
    follow_up = unique_skills(
        tuple(skill for skill in follow_up if skill != primary and skill not in prerequisites)
    )
    next_action: NextAction
    if primary is None:
        next_action = "answer_directly"
    elif prerequisites:
        next_action = "invoke_prerequisite"
    else:
        next_action = "invoke_primary_skill"
    return RoutingDecision(
        primary_skill=primary,
        prerequisites=prerequisites,
        follow_up=follow_up,
        reason=reason,
        confidence=confidence,
        next_action=next_action,
    )


def route_request(request: str, facts: RepositoryFacts | None = None) -> RoutingDecision:
    """Classify one request using stable precedence and repository facts."""
    facts = facts or RepositoryFacts()
    text = normalize_request(request)
    if not text:
        raise ValueError("request must not be empty")

    explicit = named_skills(text)
    approved_plan = facts.approved_plan_available or contains_any(
        text,
        ("approved plan", "finalized plan", "finalised plan", "written plan"),
    )
    issue_context = facts.issue_context_available or bool(
        re.search(r"(?:github\s+)?issue\s*#?\d+", text)
    )
    implementation_requested = any(has_word(text, word) for word in IMPLEMENT_WORDS)
    planning_requested = contains_any(text, PLAN_WORDS)
    orientation_requested = contains_any(text, ORIENTATION_PHRASES)

    if explicit:
        explicit_set = set(explicit)
        if {"map-codebase", "plan-change", "implement-plan"}.issubset(explicit_set):
            return make_decision(
                "plan-change",
                "explicit_map_plan_implementation_chain",
                prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
                follow_up=("implement-plan",),
            )
        if {"design-codebase", "plan-change"}.issubset(explicit_set):
            follow_up: tuple[Skill, ...] = ("plan-change",)
            if "implement-plan" in explicit_set:
                follow_up += ("implement-plan",)
            return make_decision(
                "design-codebase",
                "explicit_design_chain",
                follow_up=follow_up,
            )
        if "implement-plan" in explicit_set and not approved_plan:
            return make_decision(
                "plan-change",
                "implementation_requires_approved_plan",
                prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
                follow_up=("implement-plan",),
            )
        if "plan-change" in explicit_set and "implement-plan" in explicit_set:
            return make_decision(
                "plan-change",
                "explicit_plan_implementation_chain",
                follow_up=("implement-plan",),
            )
        return make_decision(explicit[0], "explicit_skill_request")

    if approved_plan and implementation_requested:
        return make_decision("implement-plan", "approved_plan_execution")

    if contains_any(text, RAISE_ISSUE_PHRASES) and ("handoff" in text or "raise" in text or "publish" in text or "create" in text):
        return make_decision("raise-issue", "audit_handoff_publication")
    if issue_context or contains_any(text, ISSUE_PHRASES):
        return make_decision("scope-issue", "github_issue_work")

    manual_requested = contains_any(text, MANUAL_NOUNS) and contains_any(
        text,
        ("audit", "document", "draft", "revise", "write"),
    )
    if manual_requested:
        return make_decision("manualize", "technical_manual_work")

    if contains_any(text, DIAGRAM_PHRASES):
        return make_decision("diagram-codebase", "diagram_requested")

    if contains_any(text, DESIGN_PHRASES) and contains_any(
        text,
        ("choose", "decide", "design", "redesign", "restructure", "change", "implement", "build"),
    ):
        follow_up = ()
        if planning_requested or implementation_requested:
            follow_up = ("plan-change",)
            if implementation_requested:
                follow_up += ("implement-plan",)
        return make_decision(
            "design-codebase",
            "structural_design_requested",
            prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
            follow_up=follow_up,
        )

    if contains_any(text, AUDIT_PHRASES):
        follow_up = ("plan-change", "implement-plan") if implementation_requested else ()
        return make_decision(
            "audit-codebase",
            "unknown_risk_discovery",
            follow_up=follow_up,
        )

    if contains_any(text, OPTIMIZATION_NOUNS) and contains_any(text, OPTIMIZATION_VERBS):
        return make_decision("optimize-codebase", "named_optimization_work")

    if planning_requested or implementation_requested:
        follow_up = ("implement-plan",) if implementation_requested else ()
        return make_decision(
            "plan-change",
            "source_change_requires_plan",
            prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
            follow_up=follow_up,
        )

    if orientation_requested:
        return make_decision("map-codebase", "repository_orientation")

    return make_decision(None, "no_suite_workflow_needed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    request_group = parser.add_mutually_exclusive_group(required=True)
    request_group.add_argument("--request", help="Request text to classify")
    request_group.add_argument(
        "--request-file",
        type=Path,
        help="Existing UTF-8 text file containing the request",
    )
    parser.add_argument("--repo-root", type=Path, help="Existing repository directory")
    parser.add_argument("--approved-plan", type=Path, help="Existing approved plan file")
    parser.add_argument("--issue-number", type=int, help="Known positive GitHub issue number")
    parser.add_argument(
        "--repository-navigation-inadequate",
        choices=("true",),
        help="Explicit caller signal that native navigation was insufficient.",
    )
    return parser


def validated_inputs(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> tuple[str, RepositoryFacts]:
    if args.request_file is not None:
        if not args.request_file.is_file():
            parser.error(f"request file does not exist: {args.request_file}")
        try:
            request = args.request_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            parser.error(f"request file is not valid UTF-8: {args.request_file}")
    else:
        request = args.request

    if request is None or not request.strip():
        parser.error("request must not be empty")
    if args.repo_root is not None and not args.repo_root.is_dir():
        parser.error(f"repository root does not exist: {args.repo_root}")
    if args.approved_plan is not None and not args.approved_plan.is_file():
        parser.error(f"approved plan does not exist: {args.approved_plan}")
    if args.issue_number is not None and args.issue_number <= 0:
        parser.error("issue number must be positive")

    return request, RepositoryFacts(
        repository_available=args.repo_root is not None,
        approved_plan_available=args.approved_plan is not None,
        issue_context_available=args.issue_number is not None,
        repository_navigation_inadequate=args.repository_navigation_inadequate == "true",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request, facts = validated_inputs(parser, args)
    try:
        decision = route_request(request, facts)
    except ValueError as exc:
        parser.error(str(exc))
    json.dump(decision.to_dict(), sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
