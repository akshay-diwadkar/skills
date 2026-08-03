#!/usr/bin/env python3
"""Validate an agent-selected workflow across repository skills without executing it.

The agent decides whether skills are needed, which skills to select, the primary
skill, exclusions, and user intent. This script never inspects or classifies the
request text; it only validates the supplied selection against a declarative
skill graph and returns `{valid, workflow, errors, warnings, route_handoff}`.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal, Sequence

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
SKILLS_SET: Final[frozenset[str]] = frozenset(SKILLS)
SKILL_DESCRIPTIONS: Final[dict[str, str]] = {
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
SKILL_PRECONDITIONS: Final[dict[str, str]] = {
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
SKILL_EXPECTED_ARTIFACTS: Final[dict[str, str]] = {
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

# Declarative skill graph: capabilities, artifacts, prerequisites, gates.
SKILL_CAPABILITIES: Final[dict[str, tuple[str, ...]]] = {
    "map-codebase": ("repository-navigation",),
    "design-codebase": ("structural-design",),
    "plan-change": ("implementation-planning",),
    "implement-plan": ("implementation",),
    "audit-codebase": ("risk-discovery",),
    "optimize-codebase": ("bottleneck-optimization",),
    "scope-issue": ("issue-grounding",),
    "diagram-codebase": ("visualization",),
    "manualize": ("technical-writing",),
    "raise-issue": ("issue-publication",),
    "ideate": ("ideation",),
}
SKILL_OUTPUTS: Final[dict[str, str]] = {
    "map-codebase": "repository navigation insights",
    "design-codebase": "design-handoff.md",
    "plan-change": "docs/plans/*.md",
    "implement-plan": "minimal codebase patch",
    "audit-codebase": "audit-handoff.md",
    "optimize-codebase": "optimization-handoff.md",
    "scope-issue": "issue-handoff.md",
    "diagram-codebase": "self-contained HTML diagram",
    "manualize": "source-grounded manual or audit report",
    "raise-issue": "published GitHub issues",
    "ideate": "ideas.md",
}
# Ordering edges applied when both skills are selected (stable topological reorder).
ORDERING_EDGES: Final[tuple[tuple[str, str], ...]] = (
    ("audit-codebase", "raise-issue"),
    ("design-codebase", "plan-change"),
    ("optimize-codebase", "plan-change"),
    ("scope-issue", "plan-change"),
    ("audit-codebase", "plan-change"),
    ("ideate", "design-codebase"),
    ("ideate", "plan-change"),
    ("plan-change", "implement-plan"),
)
# Mutually exclusive selections that cannot form one workflow.
INCOMPATIBLE_WITH: Final[dict[str, tuple[str, ...]]] = {
    "implement-plan": ("ideate",),
    "ideate": ("implement-plan",),
    "design-codebase": ("optimize-codebase",),
    "optimize-codebase": ("design-codebase",),
}


@dataclass(frozen=True)
class Requirement:
    """Artifact (or context) a skill requires before it can run."""

    artifact: str
    producers: tuple[str, ...] = ()
    fact: str | None = None


@dataclass(frozen=True)
class Gate:
    """Approval gate no selected skill can open by itself."""

    name: str
    fact: str
    label: str


SKILL_REQUIREMENTS: Final[dict[str, tuple[Requirement, ...]]] = {
    "raise-issue": (
        Requirement("audit-handoff.md", producers=("audit-codebase",), fact="audit_handoff_available"),
    ),
    "implement-plan": (
        Requirement("docs/plans/*.md", producers=("plan-change",), fact="approved_plan_available"),
    ),
    "scope-issue": (
        Requirement("GitHub issue context", fact="issue_context_available"),
    ),
}
SKILL_GATES: Final[dict[str, tuple[Gate, ...]]] = {
    "implement-plan": (
        Gate(
            name="plan.approved",
            fact="approved_plan_available",
            label="an approved implementation plan (`docs/plans/*.md`) that only user approval can create",
        ),
    ),
}


@dataclass(frozen=True)
class KnownFacts:
    audit_handoff_available: bool = False
    approved_plan_available: bool = False
    issue_context_available: bool = False
    repository_navigation_inadequate: bool = False


FACT_NAMES: Final[tuple[str, ...]] = tuple(
    name for name in KnownFacts.__dataclass_fields__
)

ALLOWED_ACTIONS: Final[tuple[str, ...]] = (
    "read_agent_selection",
    "read_known_facts",
    "validate_workflow",
    "emit_route_handoff",
)
FORBIDDEN_ACTIONS: Final[tuple[str, ...]] = (
    "classify_request_text",
    "plan",
    "edit_source",
    "publish_issues",
    "commit",
    "push",
    "create_pull_request",
    "execute_selected_workflow",
)


@dataclass(frozen=True)
class AgentDecision:
    """Agent-chosen workflow inputs; the script never derives them from text."""

    selected_skills: tuple[str, ...]
    primary_skill: str | None = None
    rationale: str = ""
    intent: str = ""
    excluded_skills: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    known_facts: KnownFacts = field(default_factory=KnownFacts)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    skill: str | None = None
    requires: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "skill": self.skill,
            "requires": self.requires,
            "message": self.message,
        }


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    workflow: tuple[str, ...]
    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...]
    route_handoff: str

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "workflow": list(self.workflow),
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "route_handoff": self.route_handoff,
        }


def _issue(
    code: str,
    message: str,
    *,
    skill: str | None = None,
    requires: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, skill=skill, requires=requires)


def normalize_text(value: str) -> str:
    """Return a stable presentation form for intent echo (never classification)."""
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split())


def unique_preserving_order(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def topological_order(
    selected: tuple[str, ...],
    edges: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, ...] | None, list[str]]:
    """Stable topological order preserving selection order among unrelated skills.

    Returns (order, cycle_members); order is None when the selected skills form
    a dependency cycle. The reorder only permutes the supplied skills; it never
    adds, removes, or chooses a skill.
    """
    nodes = list(selected)
    outgoing: dict[str, list[str]] = {node: [] for node in nodes}
    indegree: dict[str, int] = {node: 0 for node in nodes}
    for source, target in edges:
        if source in outgoing and target in outgoing and target not in outgoing[source]:
            outgoing[source].append(target)
            indegree[target] += 1
    ordered: list[str] = []
    remaining = list(nodes)
    while remaining:
        ready = [node for node in remaining if indegree[node] == 0]
        if not ready:
            cycle_members = [node for node in remaining if indegree[node] > 0]
            return None, cycle_members
        chosen = ready[0]
        ordered.append(chosen)
        remaining.remove(chosen)
        for target in outgoing[chosen]:
            indegree[target] -= 1
    return tuple(ordered), []


def _ordering_edges(selected: tuple[str, ...], facts: KnownFacts) -> tuple[tuple[str, str], ...]:
    edges = list(ORDERING_EDGES)
    if facts.repository_navigation_inadequate and "map-codebase" in selected and len(selected) > 1:
        for other in selected:
            if other != "map-codebase":
                edges.append(("map-codebase", other))
    return tuple(edges)


def _artifacts_available_before(
    workflow: tuple[str, ...],
    skill: str,
) -> tuple[str, ...]:
    produced: list[str] = []
    for name in workflow:
        if name == skill:
            break
        output = SKILL_OUTPUTS.get(name)
        if output:
            produced.append(output)
    return tuple(produced)


def validate_workflow(decision: AgentDecision, detail: str = "compact") -> ValidationResult:
    """Validate the agent-selected workflow without classifying any text."""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    facts = decision.known_facts
    selected = unique_preserving_order(decision.selected_skills)
    selected_set = set(selected)
    excluded_set = set(decision.excluded_skills)
    if detail not in {"compact", "detailed"}:
        detail = "compact"

    for name in selected:
        if name not in SKILLS_SET:
            errors.append(
                _issue(
                    "selection.unknown_skill",
                    f"selected skill {name!r} is not a routable skill; choose from {', '.join(SKILLS)}.",
                    skill=name,
                )
            )
    seen: set[str] = set()
    for name in decision.selected_skills:
        if name in SKILLS_SET and name in seen:
            errors.append(
                _issue(
                    "selection.duplicate",
                    f"skill {name!r} is selected more than once; select each skill exactly once.",
                    skill=name,
                )
            )
        seen.add(name)

    for name in decision.excluded_skills:
        if name not in SKILLS_SET:
            errors.append(
                _issue(
                    "selection.excluded_unknown",
                    f"excluded skill {name!r} is not a routable skill; choose from {', '.join(SKILLS)}.",
                    skill=name,
                )
            )
        elif name not in selected_set:
            warnings.append(
                _issue(
                    "selection.exclusion_inert",
                    f"excluded skill {name!r} is not in selected_skills, so the exclusion has no effect.",
                    skill=name,
                )
            )

    primary = decision.primary_skill
    if primary is not None:
        if primary not in SKILLS_SET:
            errors.append(
                _issue(
                    "selection.unknown_skill",
                    f"primary skill {primary!r} is not a routable skill; choose from {', '.join(SKILLS)}.",
                    skill=primary,
                )
            )
        elif primary in excluded_set:
            errors.append(
                _issue(
                    "selection.excluded_primary",
                    f"primary skill {primary!r} is also in excluded_skills; reconcile the selection.",
                    skill=primary,
                )
            )
        elif primary not in selected_set:
            errors.append(
                _issue(
                    "selection.primary_not_selected",
                    f"primary skill {primary!r} is not in selected_skills; add it or choose a different primary.",
                    skill=primary,
                )
            )

    covered_capabilities: set[str] = set()
    for name in selected:
        if name in SKILLS_SET:
            covered_capabilities.update(SKILL_CAPABILITIES.get(name, ()))
    for capability in decision.required_capabilities:
        if capability not in covered_capabilities:
            errors.append(
                _issue(
                    "capability.missing",
                    f"no selected skill provides required capability {capability!r}; "
                    f"add a skill with that capability or remove it from required_capabilities.",
                    requires=capability,
                )
            )

    valid_selected = tuple(name for name in selected if name in SKILLS_SET)
    for index, name in enumerate(valid_selected):
        for other in valid_selected[index + 1 :]:
            if other in INCOMPATIBLE_WITH.get(name, ()):
                errors.append(
                    _issue(
                        "compatibility.conflict",
                        f"{name} and {other} are incompatible in one workflow; remove one of them.",
                        skill=name,
                        requires=other,
                    )
                )

    for name in valid_selected:
        for requirement in SKILL_REQUIREMENTS.get(name, ()):
            producer_selected = any(producer in selected_set for producer in requirement.producers)
            fact_true = requirement.fact is not None and bool(getattr(facts, str(requirement.fact)))
            if producer_selected or fact_true:
                continue
            excluded_producer = next(
                (producer for producer in requirement.producers if producer in excluded_set),
                None,
            )
            if excluded_producer is not None:
                errors.append(
                    _issue(
                        "dependency.excluded_prerequisite",
                        f"{name} requires {requirement.artifact}, which is produced by "
                        f"{excluded_producer}, but that skill is excluded; unexclude it or declare "
                        f"{requirement.fact}=true.",
                        skill=name,
                        requires=requirement.artifact,
                    )
                )
                continue
            if requirement.fact is not None:
                errors.append(
                    _issue(
                        "dependency.missing_artifact",
                        f"{name} requires {requirement.artifact}; add {', '.join(requirement.producers)} "
                        f"to selected_skills or set {requirement.fact}=true.",
                        skill=name,
                        requires=requirement.artifact,
                    )
                )
            else:
                errors.append(
                    _issue(
                        "dependency.missing_artifact",
                        f"{name} requires {requirement.artifact}; satisfy the requirement before rerunning.",
                        skill=name,
                        requires=requirement.artifact,
                    )
                )

    for name in valid_selected:
        for gate in SKILL_GATES.get(name, ()):
            if not bool(getattr(facts, gate.fact)):
                errors.append(
                    _issue(
                        "gate.approval_required",
                        f"{name} requires {gate.label}; set {gate.fact}=true or remove {name} "
                        f"from selected_skills.",
                        skill=name,
                        requires=gate.fact,
                    )
                )

    if "raise-issue" in selected_set:
        warnings.append(
            _issue(
                "warn.publication_approval",
                "raise-issue publishes GitHub issues only after separate user approval; "
                "route-work cannot grant publication authority.",
                skill="raise-issue",
            )
        )

    edges = _ordering_edges(valid_selected, facts)
    reordered, cycle_members = topological_order(valid_selected, edges)
    if reordered is None:
        errors.append(
            _issue(
                "order.cycle",
                "selected skills form a dependency cycle that cannot be ordered: "
                + ", ".join(cycle_members)
                + ". Remove one skill from the cycle and rerun.",
            )
        )
    valid = not errors
    workflow = reordered if (valid and reordered is not None) else valid_selected
    handoff = generate_route_handoff(decision, valid, workflow, errors, warnings, detail=detail)
    return ValidationResult(
        valid=valid,
        workflow=workflow,
        errors=tuple(errors),
        warnings=tuple(warnings),
        route_handoff=handoff,
    )


def generate_mermaid_diagram(workflow: tuple[str, ...]) -> str:
    """Construct a clean Mermaid flowchart for the validated workflow."""
    if not workflow:
        return (
            "```mermaid\n"
            "flowchart TD\n"
            '    Start(["Start Task Request"]) --> End(["Task Complete"])\n'
            "```"
        )

    lines: list[str] = ["```mermaid", "flowchart TD", '    Start(["Start Task Request"])']
    prev_node = "Start"

    for index, skill in enumerate(workflow, start=1):
        curr_node = f"Step{index}"
        label = f'"{index}. {skill}<br/>{SKILL_DESCRIPTIONS[skill]}"'
        lines.append(f"    {prev_node} --> {curr_node}[{label}]")
        prev_node = curr_node

        if skill == "plan-change" and "implement-plan" in workflow[index:]:
            approval_node = f"BranchApproval{index}"
            lines.append(f'    {curr_node} --> {approval_node}{{"Plan Approved?"}}')
            lines.append(f'    {approval_node} -- "No / Revisions Needed" --> {curr_node}')
            prev_node = f"{approval_node} -- \"Yes\""

        elif skill == "implement-plan":
            verify_node = f"BranchVerify{index}"
            lines.append(f'    {curr_node} --> {verify_node}{{"Verification Passed?"}}')
            lines.append(f'    {verify_node} -- "Fail / Fix Needed" --> {curr_node}')
            prev_node = f'{verify_node} -- "Pass"'

        elif skill == "audit-codebase" and "raise-issue" in workflow[index:]:
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
    decision: AgentDecision,
    valid: bool,
    workflow: tuple[str, ...],
    errors: Sequence[ValidationIssue],
    warnings: Sequence[ValidationIssue],
    detail: str = "compact",
) -> str:
    """Generate the route-handoff Markdown document from the validated workflow."""
    mermaid = generate_mermaid_diagram(workflow)
    facts = decision.known_facts
    fact_rows = ", ".join(
        f"`{name}: {bool(getattr(facts, name))}`" for name in FACT_NAMES
    )

    lines: list[str] = [
        "# Route Handoff Guidance",
        "",
        "## Decision Overview",
        "",
        f"- **Validation:** `{'valid' if valid else 'invalid'}`",
        f"- **Primary Skill:** `{decision.primary_skill if decision.primary_skill else 'none'}`",
        f"- **Selected Skills:** {', '.join(f'`{name}`' for name in decision.selected_skills) or '`none`'}",
    ]
    if decision.excluded_skills:
        lines.append(
            f"- **Excluded Skills:** {', '.join(f'`{name}`' for name in decision.excluded_skills)}"
        )
    if decision.required_capabilities:
        lines.append(
            "- **Required Capabilities:** "
            + ", ".join(f"`{name}`" for name in decision.required_capabilities)
        )
    if any(bool(getattr(facts, name)) for name in FACT_NAMES):
        lines.append(f"- **Known Facts:** {fact_rows}")
    if decision.intent:
        lines.append(f"- **Intent:** {decision.intent}")
    if decision.rationale:
        lines.append(f"- **Rationale:** {decision.rationale}")
    lines.extend(
        [
            "",
            "## Workflow Route Diagram",
            "",
            mermaid,
            "",
        ]
    )

    if errors:
        lines.extend(["## Validation Errors", ""])
        for index, issue in enumerate(errors, start=1):
            lines.append(f"{index}. `{issue.code}` — {issue.message}")
        lines.append("")

    if warnings:
        lines.extend(["## Validation Warnings", ""])
        for index, issue in enumerate(warnings, start=1):
            lines.append(f"{index}. `{issue.code}` — {issue.message}")
        lines.append("")

    if detail == "detailed":
        if workflow:
            lines.extend(["## Route Steps", ""])
            for index, skill in enumerate(workflow, start=1):
                lines.append(f"{index}. `{skill}` — {SKILL_DESCRIPTIONS[skill]}")
            lines.append("")
        lines.extend(["## Step-by-Step Execution Guidance", ""])
        if not workflow:
            lines.extend(
                [
                    "No heavyweight suite workflow is required for this selection.",
                    "",
                ]
            )
        else:
            for index, skill in enumerate(workflow, start=1):
                lines.extend(
                    [
                        f"### Step {index}: `{skill}`",
                        f"- **Purpose:** {SKILL_DESCRIPTIONS[skill]}",
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
                "4. **Re-route When Scope Expands:** If the agent selection introduces new requirements, run `route-work` again with an updated selection.",
                "",
            ]
        )

    return "\n".join(lines)


SKILL_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
HANDOFF_FILENAME = "route-handoff.md"


def canonical_path(path: Path) -> Path:
    """Resolve existing symlinked ancestors of a possibly-future path."""
    return path.expanduser().resolve(strict=False)


def is_within(path: Path, parent: Path) -> bool:
    """True when path equals or descends from parent (canonical containment)."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def handoff_destination(output_file: Path | None, output_dir: Path | None) -> Path | None:
    """Return the canonical file a handoff write would create, if any."""
    if output_file is not None:
        return canonical_path(output_file)
    if output_dir is not None:
        return canonical_path(output_dir / HANDOFF_FILENAME)
    return None


def unsafe_handoff_root(
    destination: Path, protected_roots: tuple[Path, ...]
) -> Path | None:
    """Return the first protected root containing the destination, or None."""
    for root in protected_roots:
        if is_within(destination, root):
            return root
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selected-skill",
        action="append",
        default=[],
        help="Agent-selected skill (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--primary-skill",
        choices=SKILLS,
        help="Agent-chosen primary skill; must be in selected_skills",
    )
    parser.add_argument("--rationale", help="Agent rationale; echoed verbatim, never analyzed")
    parser.add_argument("--intent", help="Agent-stated user intent; echoed verbatim, never analyzed")
    parser.add_argument(
        "--excluded-skill",
        action="append",
        default=[],
        help="Skill the agent explicitly excluded (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--required-capability",
        action="append",
        default=[],
        help="Capability the selected workflow must cover (repeatable or comma-separated)",
    )
    for name in FACT_NAMES:
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            choices=("true",),
            help=f"Known fact: {name}=true",
        )
    parser.add_argument("--repo-root", type=Path, help="Existing repository directory")
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


def _flatten(values: list[str]) -> list[str]:
    parts: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                parts.append(part)
    return parts


def validated_inputs(parser: argparse.ArgumentParser, args: argparse.Namespace) -> AgentDecision:
    if args.repo_root is not None and not args.repo_root.is_dir():
        parser.error(f"repository root does not exist: {args.repo_root}")
    selected = _flatten(args.selected_skill)
    if not selected:
        parser.error("at least one --selected-skill is required")
    destination = handoff_destination(args.output_file, args.output_dir)
    if destination is not None:
        repository = args.repo_root.resolve() if args.repo_root is not None else None
        protected_roots = tuple(root for root in (SKILL_ROOT, repository) if root is not None)
        if unsafe_handoff_root(destination, protected_roots) is not None:
            parser.error(
                "handoff output must be outside the repository and installed skill: "
                f"{destination}"
            )
    if args.output_dir is not None and not args.output_dir.is_dir():
        parser.error(f"output directory does not exist: {args.output_dir}")

    facts = KnownFacts(
        audit_handoff_available=args.audit_handoff_available == "true",
        approved_plan_available=args.approved_plan_available == "true",
        issue_context_available=args.issue_context_available == "true",
        repository_navigation_inadequate=args.repository_navigation_inadequate == "true",
    )
    return AgentDecision(
        selected_skills=tuple(selected),
        primary_skill=args.primary_skill,
        rationale=normalize_text(args.rationale or ""),
        intent=normalize_text(args.intent or ""),
        excluded_skills=tuple(_flatten(args.excluded_skill)),
        required_capabilities=tuple(_flatten(args.required_capability)),
        known_facts=facts,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    decision = validated_inputs(parser, args)
    result = validate_workflow(decision, detail=args.handoff)

    if args.output_file is not None:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(result.route_handoff, encoding="utf-8")
    elif args.output_dir is not None:
        (args.output_dir / HANDOFF_FILENAME).write_text(result.route_handoff, encoding="utf-8")

    json.dump(result.to_dict(), sys.stdout, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
