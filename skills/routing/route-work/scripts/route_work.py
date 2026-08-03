#!/usr/bin/env python3
"""Deterministically route a work request across repository skills without executing a workflow."""

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
    "ideate",
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
    "ideate",
)
SKILL_DESCRIPTIONS: Final[dict[Skill, str]] = {
    "map-codebase": "Explore an unfamiliar repository and locate the files or symbols that own a requested change.",
    "design-codebase": "Decide structural boundaries, dependency directions, and state ownership before drafting a plan.",
    "plan-change": "Explore repository proof natively and draft a sealed implementation plan for code modifications.",
    "implement-plan": "Execute an approved implementation plan as a minimal patch while preserving repository contracts.",
    "audit-codebase": "Discover confirmed security risks, bugs, test gaps, and code quality problems across the repository.",
    "optimize-codebase": "Identify evidence-backed performance or maintainability bottlenecks and benchmark improvements.",
    "scope-issue": "Ground a GitHub issue in repository reality and prepare an issue handoff for planning.",
    "diagram-codebase": "Generate visual architecture, workflow, or system diagrams as self-contained HTML artifacts.",
    "manualize": "Write or audit source-grounded manuals, procedures, runbooks, guides, error messages, or documentation.",
    "raise-issue": "Preview and publish sealed audit handoffs as GitHub issues.",
    "ideate": "Generate and rank candidate ideas for your feature or research goals before committing to a design.",
}
SKILL_PRECONDITIONS: Final[dict[Skill, str]] = {
    "map-codebase": "Unfamiliar repository or unmapped entrypoints/symbols.",
    "design-codebase": "Candidate idea selected or high-level architectural change required.",
    "plan-change": "Grounded scope or sealed handoff artifact (design, issue, audit, or optimization).",
    "implement-plan": "Sealed and user-approved implementation plan artifact (`docs/plans/*.md`).",
    "audit-codebase": "Target repository checkout available for read-only inspection.",
    "optimize-codebase": "Target repository checkout with observable or measured bottleneck.",
    "scope-issue": "GitHub issue ID or issue details available for grounding.",
    "diagram-codebase": "Target system, architecture, or workflow concept to visualize.",
    "manualize": "Target documentation, runbook, or reference guide to audit or write.",
    "raise-issue": "Sealed audit handoff (`audit-handoff.md`) with confirmed issues.",
    "ideate": "Clear problem statement, research target, or feature objective.",
}
SKILL_EXPECTED_ARTIFACTS: Final[dict[Skill, str]] = {
    "map-codebase": "Repository navigation insights & bounded symbol paths",
    "design-codebase": "`design-handoff.md`",
    "plan-change": "`docs/plans/*.md` (v6 implementation plan draft)",
    "implement-plan": "Minimal codebase patch & verification test report",
    "audit-codebase": "`audit-handoff.md`",
    "optimize-codebase": "`optimization-handoff.md`",
    "scope-issue": "`issue-handoff.md`",
    "diagram-codebase": "Self-contained HTML diagram artifact",
    "manualize": "Source-grounded manual or documentation audit report",
    "raise-issue": "Published GitHub issues & issue URLs",
    "ideate": "`ideas.md`",
}

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
    "execute",
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
    "architecture",
    "architecture decision",
    "architecture design",
    "boundary",
    "boundaries",
    "dependency direction",
    "design architecture",
    "state ownership",
    "abstraction",
    "subsystem design",
    "structural design",
    "redesign",
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
    "create issue",
    "create issues",
    "publish issue",
    "publish issues",
    "raise issue",
    "raise issues",
    "triage issue",
    "scope issue",
)
IDEATE_PHRASES: Final[tuple[str, ...]] = (
    "ideate",
    "brainstorm",
    "candidate ideas",
    "generate ideas",
    "rank ideas",
    "feature ideas",
    "research options",
    "explore possibilities",
)
HANDOFF_PHRASES: Final[tuple[str, ...]] = ("audit-handoff", "audit handoff")
PUBLICATION_WORDS: Final[tuple[str, ...]] = ("create", "open", "publish", "raise")


@dataclass(frozen=True)
class RepositoryFacts:
    repository_available: bool = False
    approved_plan_available: bool = False
    issue_context_available: bool = False
    repository_navigation_inadequate: bool = False


@dataclass(frozen=True)
class WorkflowStep:
    skill: Skill
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "skill": self.skill,
            "description": self.description,
        }


@dataclass(frozen=True)
class RoutingDecision:
    primary_skill: Skill | None
    prerequisites: tuple[Skill, ...]
    follow_up: tuple[Skill, ...]
    workflow: tuple[WorkflowStep, ...]
    route_handoff: str
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
            "workflow": [step.to_dict() for step in self.workflow],
            "route_handoff": self.route_handoff,
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


def generate_mermaid_diagram(
    primary: Skill | None,
    prerequisites: tuple[Skill, ...],
    follow_up: tuple[Skill, ...],
    workflow: tuple[WorkflowStep, ...],
) -> str:
    """Construct a clean Mermaid flowchart representing the route, branches, and loops."""
    if primary is None or not workflow:
        return (
            "```mermaid\n"
            "flowchart TD\n"
            '    Start(["User Request"]) --> Direct["Answer Directly / Standard Tool Use"]\n'
            '    Direct --> End(["Task Complete"])\n'
            "```"
        )

    lines: list[str] = ["```mermaid", "flowchart TD", '    Start(["Start Task Request"])']
    prev_node = "Start"

    skills_in_order = [step.skill for step in workflow]

    for index, skill in enumerate(skills_in_order, start=1):
        curr_node = f"Step{index}"
        label = f'"{index}. {skill}<br/>{SKILL_DESCRIPTIONS[skill]}"'
        lines.append(f"    {prev_node} --> {curr_node}[{label}]")
        prev_node = curr_node

        if skill == "plan-change" and "implement-plan" in skills_in_order[index:]:
            approval_node = f"BranchApproval{index}"
            lines.append(f'    {curr_node} --> {approval_node}{{"Plan Approved?"}}')
            lines.append(f'    {approval_node} -- "No / Revisions Needed" --> {curr_node}')
            prev_node = f"{approval_node} -- \"Yes\""

        elif skill == "implement-plan":
            verify_node = f"BranchVerify{index}"
            lines.append(f'    {curr_node} --> {verify_node}{{"Verification Passed?"}}')
            lines.append(f'    {verify_node} -- "Fail / Fix Needed" --> {curr_node}')
            prev_node = f'{verify_node} -- "Pass"'

        elif skill == "audit-codebase" and "raise-issue" in skills_in_order[index:]:
            pub_node = f"BranchPub{index}"
            lines.append(f'    {curr_node} --> {pub_node}{{"Publish Issues?"}}')
            lines.append(f'    {pub_node} -- "No" --> End(["Task Complete"])')
            prev_node = f'{pub_node} -- "Yes"'

        else:
            prev_node = curr_node

    lines.append(f'    {prev_node} --> End(["Task Complete"])')
    lines.append("```")
    return "\n".join(lines)


def generate_route_handoff(
    request: str,
    primary: Skill | None,
    prerequisites: tuple[Skill, ...],
    follow_up: tuple[Skill, ...],
    workflow: tuple[WorkflowStep, ...],
    reason: str,
    confidence: Confidence,
    next_action: NextAction,
    detail: str = "compact",
) -> str:
    """Generate the route-handoff Markdown document.

    The compact document is the default routing decision summary; the detailed
    document adds per-step execution guidance and quick-start instructions and
    is generated only on explicit request.
    """
    mermaid = generate_mermaid_diagram(primary, prerequisites, follow_up, workflow)

    lines: list[str] = [
        "# Route Handoff Guidance",
        "",
        "## Request Overview",
        "",
        f'- **User Request:** "{request}"',
        f"- **Primary Skill:** `{primary if primary else 'null (Direct Answer)'}`",
        f"- **Confidence:** `{confidence}`",
        f"- **Reason:** `{reason}`",
        f"- **Next Action:** `{next_action}`",
        "",
        "## Workflow Route Diagram",
        "",
        mermaid,
        "",
    ]

    if not workflow:
        lines.extend(
            [
                "No heavyweight suite workflow is required for this request.",
                "Provide a direct answer or perform standard file inspection using native tools.",
                "",
            ]
        )
    else:
        lines.extend(["## Route Steps", ""])
        for idx, step in enumerate(workflow, start=1):
            lines.append(f"{idx}. `{step.skill}` — {step.description}")
        lines.append("")

    if detail == "detailed":
        lines.extend(["## Step-by-Step Execution Guidance", ""])
        if not workflow:
            lines.extend(
                [
                    "No heavyweight suite workflow is required for this request.",
                    "Provide a direct answer or perform standard file inspection using native tools.",
                    "",
                ]
            )
        else:
            for idx, step in enumerate(workflow, start=1):
                skill = step.skill
                lines.extend(
                    [
                        f"### Step {idx}: `{skill}`",
                        f"- **Purpose:** {step.description}",
                        f"- **Preconditions:** {SKILL_PRECONDITIONS.get(skill, 'N/A')}",
                        f"- **Actionable Guidance:** Execute `{skill}` to perform this phase. "
                        + (
                            "Verify and seal plan before implementation."
                            if skill == "plan-change"
                            else (
                                "Apply minimal patch and verify clean test execution."
                                if skill == "implement-plan"
                                else "Inspect repository proof and produce required handoff artifact."
                            )
                        ),
                        "- **Branching & Loop Conditions:** "
                        + (
                            "If plan requires changes, loop back within `plan-change` before requesting approval. Proceed to `implement-plan` only after explicit user approval."
                            if skill == "plan-change"
                            else (
                                "If tests or verification fail, diagnose root cause and apply targeted fix before finalizing. Loop back to `plan-change` if structural scope changes."
                                if skill == "implement-plan"
                                else "Proceed to next step upon artifact completion."
                            )
                        ),
                        f"- **Expected Artifact:** {SKILL_EXPECTED_ARTIFACTS.get(skill, 'None')}",
                        "",
                    ]
                )
        lines.extend(
            [
                "## Quick Start for New Users",
                "",
                "1. **Follow the Route:** Execute the skills in the exact order shown above.",
                "2. **Respect Decision Gates:** Never jump to execution (`implement-plan`) without an approved plan (`docs/plans/*.md`).",
                "3. **Handle Loopbacks:** If verification tests fail during implementation, analyze full error logs and fix cleanly without swallowing errors.",
                "4. **Re-route When Scope Expands:** If the user request introduces new requirements, run `route-work` again for updated guidance.",
                "",
            ]
        )

    return "\n".join(lines)


def make_decision(
    primary: Skill | None,
    reason: str,
    request: str,
    *,
    prerequisites: tuple[Skill, ...] = (),
    follow_up: tuple[Skill, ...] = (),
    confidence: Confidence = "high",
    handoff_detail: str = "compact",
) -> RoutingDecision:
    prerequisites = unique_skills(tuple(skill for skill in prerequisites if skill != primary))
    follow_up = unique_skills(
        tuple(skill for skill in follow_up if skill != primary and skill not in prerequisites)
    )
    raw_sequence = prerequisites + ((primary,) if primary else ()) + follow_up
    workflow = tuple(
        WorkflowStep(skill=skill, description=SKILL_DESCRIPTIONS[skill])
        for skill in unique_skills(raw_sequence)
    )
    next_action: NextAction
    if primary is None:
        next_action = "answer_directly"
    elif prerequisites:
        next_action = "invoke_prerequisite"
    else:
        next_action = "invoke_primary_skill"

    route_handoff = generate_route_handoff(
        request=request,
        primary=primary,
        prerequisites=prerequisites,
        follow_up=follow_up,
        workflow=workflow,
        reason=reason,
        confidence=confidence,
        next_action=next_action,
        detail=handoff_detail,
    )

    return RoutingDecision(
        primary_skill=primary,
        prerequisites=prerequisites,
        follow_up=follow_up,
        workflow=workflow,
        route_handoff=route_handoff,
        reason=reason,
        confidence=confidence,
        next_action=next_action,
    )


def route_request(
    request: str,
    facts: RepositoryFacts | None = None,
    handoff_detail: str = "compact",
) -> RoutingDecision:
    """Classify one request using stable precedence and repository facts.

    Precedence: explicit skill names and chains, then approved-plan execution,
    then implicit ideation detection, then the remaining evidence rules.
    Only classification uses the normalized request; the original text is
    preserved verbatim in the handoff.
    """
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
        if {"ideate", "plan-change"}.issubset(explicit_set):
            ideate_follow_up: tuple[Skill, ...] = ("plan-change",)
            if "implement-plan" in explicit_set:
                ideate_follow_up += ("implement-plan",)
            return make_decision(
                "ideate",
                "explicit_ideate_chain",
                request,
                follow_up=ideate_follow_up,
                handoff_detail=handoff_detail,
            )
        if {"map-codebase", "plan-change", "implement-plan"}.issubset(explicit_set):
            return make_decision(
                "plan-change",
                "explicit_map_plan_implementation_chain",
                request,
                prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
                follow_up=("implement-plan",),
                handoff_detail=handoff_detail,
            )
        if {"design-codebase", "plan-change"}.issubset(explicit_set):
            follow_up: tuple[Skill, ...] = ("plan-change",)
            if "implement-plan" in explicit_set:
                follow_up += ("implement-plan",)
            return make_decision(
                "design-codebase",
                "explicit_design_chain",
                request,
                follow_up=follow_up,
                handoff_detail=handoff_detail,
            )
        if "implement-plan" in explicit_set and not approved_plan:
            return make_decision(
                "plan-change",
                "implementation_requires_approved_plan",
                request,
                prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
                follow_up=("implement-plan",),
                handoff_detail=handoff_detail,
            )
        if "plan-change" in explicit_set and "implement-plan" in explicit_set:
            return make_decision(
                "plan-change",
                "explicit_plan_implementation_chain",
                request,
                follow_up=("implement-plan",),
                handoff_detail=handoff_detail,
            )
        return make_decision(
            explicit[0],
            "explicit_skill_request",
            request,
            handoff_detail=handoff_detail,
        )

    if approved_plan and implementation_requested:
        return make_decision(
            "implement-plan",
            "approved_plan_execution",
            request,
            handoff_detail=handoff_detail,
        )

    if contains_any(text, IDEATE_PHRASES):
        ideate_follow_up_skills: list[Skill] = []
        if contains_any(text, DESIGN_PHRASES) and "design-codebase" not in ideate_follow_up_skills:
            ideate_follow_up_skills.append("design-codebase")
        if (planning_requested or contains_any(text, ("plan", "draft plan"))) and "plan-change" not in ideate_follow_up_skills:
            ideate_follow_up_skills.append("plan-change")
        if implementation_requested:
            if "plan-change" not in ideate_follow_up_skills:
                ideate_follow_up_skills.append("plan-change")
            if "implement-plan" not in ideate_follow_up_skills:
                ideate_follow_up_skills.append("implement-plan")
        return make_decision(
            "ideate",
            "research_ideation_requested",
            request,
            follow_up=tuple(ideate_follow_up_skills),
            handoff_detail=handoff_detail,
        )

    if contains_any(text, HANDOFF_PHRASES) and contains_any(text, PUBLICATION_WORDS):
        return make_decision(
            "raise-issue",
            "audit_handoff_publication",
            request,
            handoff_detail=handoff_detail,
        )
    audit_requested = contains_any(text, AUDIT_PHRASES)
    publication_requested = contains_any(text, PUBLICATION_WORDS) and contains_any(
        text, ("issue", "issues")
    )
    if audit_requested and publication_requested:
        return make_decision(
            "audit-codebase",
            "unknown_risk_discovery",
            request,
            follow_up=("raise-issue",),
            handoff_detail=handoff_detail,
        )
    if issue_context or contains_any(text, ISSUE_PHRASES):
        issue_follow_up: tuple[Skill, ...] = ("plan-change",)
        if implementation_requested:
            issue_follow_up += ("implement-plan",)
        return make_decision(
            "scope-issue",
            "github_issue_work",
            request,
            follow_up=issue_follow_up,
            handoff_detail=handoff_detail,
        )

    manual_requested = contains_any(text, MANUAL_NOUNS) and contains_any(
        text,
        ("audit", "document", "draft", "revise", "write"),
    )
    if manual_requested:
        return make_decision(
            "manualize",
            "technical_manual_work",
            request,
            handoff_detail=handoff_detail,
        )

    if contains_any(text, DIAGRAM_PHRASES):
        return make_decision(
            "diagram-codebase",
            "diagram_requested",
            request,
            handoff_detail=handoff_detail,
        )

    if contains_any(text, DESIGN_PHRASES) and contains_any(
        text,
        ("choose", "decide", "design", "redesign", "restructure", "change", "implement", "build"),
    ):
        design_follow_up: tuple[Skill, ...] = ("plan-change",)
        if implementation_requested:
            design_follow_up += ("implement-plan",)
        return make_decision(
            "design-codebase",
            "structural_design_requested",
            request,
            prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
            follow_up=design_follow_up,
            handoff_detail=handoff_detail,
        )

    if audit_requested:
        audit_follow_up: tuple[Skill, ...] = ("plan-change",)
        if implementation_requested:
            audit_follow_up += ("implement-plan",)
        return make_decision(
            "audit-codebase",
            "unknown_risk_discovery",
            request,
            follow_up=audit_follow_up,
            handoff_detail=handoff_detail,
        )

    if contains_any(text, OPTIMIZATION_NOUNS) and contains_any(text, OPTIMIZATION_VERBS):
        optimization_follow_up: tuple[Skill, ...] = ("plan-change",)
        if implementation_requested:
            optimization_follow_up += ("implement-plan",)
        return make_decision(
            "optimize-codebase",
            "named_optimization_work",
            request,
            follow_up=optimization_follow_up,
            handoff_detail=handoff_detail,
        )

    if planning_requested or implementation_requested:
        follow_up = ("implement-plan",) if implementation_requested else ()
        return make_decision(
            "plan-change",
            "source_change_requires_plan",
            request,
            prerequisites=("map-codebase",) if facts.repository_navigation_inadequate else (),
            follow_up=follow_up,
            handoff_detail=handoff_detail,
        )

    if orientation_requested:
        return make_decision(
            "map-codebase",
            "repository_orientation",
            request,
            handoff_detail=handoff_detail,
        )

    return make_decision(
        None,
        "no_suite_workflow_needed",
        request,
        handoff_detail=handoff_detail,
    )


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
    parser.add_argument(
        "--handoff",
        choices=("compact", "detailed"),
        default="compact",
        help="Detailed handoff generation is opt-in; the compact routing decision is the default.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Target file path, outside the repository, to write route-handoff.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Target directory, outside the repository, to write route-handoff.md",
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
    if args.repo_root is not None:
        repository = args.repo_root.resolve()
        for label, target in (
            ("output file", args.output_file),
            ("output directory", args.output_dir),
        ):
            if target is not None and (
                target.resolve() == repository or repository in target.resolve().parents
            ):
                parser.error(f"{label} must be outside the repository: {target}")
    if args.output_dir is not None and not args.output_dir.is_dir():
        parser.error(f"output directory does not exist: {args.output_dir}")

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
        decision = route_request(request, facts, handoff_detail=args.handoff)
    except ValueError as exc:
        parser.error(str(exc))

    if args.output_file is not None:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(decision.route_handoff, encoding="utf-8")
    elif args.output_dir is not None:
        (args.output_dir / "route-handoff.md").write_text(decision.route_handoff, encoding="utf-8")

    json.dump(decision.to_dict(), sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
