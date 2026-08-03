from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "routing" / "route-work"
SCRIPT_DIR = SKILL_ROOT / "scripts"
SCRIPT = SCRIPT_DIR / "route_work.py"
SCHEMA = json.loads(
    (SKILL_ROOT / "schemas" / "routing-decision.schema.json").read_text(encoding="utf-8")
)
FIXTURES = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(SCRIPT_DIR))

from route_work import (  # noqa: E402
    ALLOWED_ACTIONS,
    FORBIDDEN_ACTIONS,
    SKILLS,
    RepositoryFacts,
    canonical_path,
    execution_requested,
    handoff_destination,
    route_request,
    unsafe_handoff_root,
)


def load_cases(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


@pytest.mark.parametrize("case", load_cases("routing-cases.json"), ids=lambda case: case["id"])
def test_deterministic_routing_fixtures(case: dict[str, object]) -> None:
    raw_facts = case["facts"]
    assert isinstance(raw_facts, dict)
    facts = RepositoryFacts(**raw_facts)
    request = case["request"]
    assert isinstance(request, str)
    expected = case["expected"]
    assert isinstance(expected, dict)

    first = route_request(request, facts).to_dict()
    second = route_request(request, facts).to_dict()

    assert first == second
    assert {key: first[key] for key in expected} == expected
    assert first["allowed_actions"] == list(ALLOWED_ACTIONS)
    assert first["forbidden_actions"] == list(FORBIDDEN_ACTIONS)
    assert "route_handoff" in first
    route_handoff = first["route_handoff"]
    assert isinstance(route_handoff, str)
    assert "# Route Handoff Guidance" in route_handoff
    assert "```mermaid" in route_handoff
    jsonschema.validate(first, SCHEMA)


@pytest.mark.parametrize(
    "case",
    load_cases("false-positive-cases.json"),
    ids=lambda case: case["id"],
)
def test_simple_requests_do_not_trigger_suite_workflows(case: dict[str, object]) -> None:
    request = case["request"]
    assert isinstance(request, str)
    decision = route_request(request).to_dict()

    assert decision["primary_skill"] is None
    assert decision["prerequisites"] == []
    assert decision["follow_up"] == []
    assert decision["workflow"] == []
    assert decision["reason"] == "no_suite_workflow_needed"
    assert decision["next_action"] == "answer_directly"
    assert "route_handoff" in decision
    route_handoff = decision["route_handoff"]
    assert isinstance(route_handoff, str)
    assert "Direct Answer" in route_handoff
    forbidden_actions = decision["forbidden_actions"]
    assert isinstance(forbidden_actions, list)
    assert "execute_selected_workflow" in forbidden_actions
    jsonschema.validate(decision, SCHEMA)


def test_normalization_is_stable_for_classification() -> None:
    canonical = route_request("Plan a migration.").to_dict()
    variant = route_request("  PLAN\u00a0a   migration.  ").to_dict()
    # Classification fields must be normalization-stable; the handoff embeds
    # the original request text verbatim and therefore differs.
    canonical.pop("route_handoff")
    variant.pop("route_handoff")
    assert variant == canonical


def test_route_handoff_preserves_original_request_text() -> None:
    request = "Fix the bug in `src/AuthService.ts` and rename FEATURE_FLAG_X to FEATURE_FLAG_Y."
    decision = route_request(request).to_dict()
    route_handoff = decision["route_handoff"]
    assert isinstance(route_handoff, str)
    assert f'**User Request:** "{request}"' in route_handoff
    assert "src/AuthService.ts" in route_handoff
    assert "FEATURE_FLAG_X" in route_handoff
    assert "FEATURE_FLAG_Y" in route_handoff


def test_compact_handoff_is_the_default_and_detailed_is_opt_in() -> None:
    compact_handoff = route_request("Plan a migration.").to_dict()["route_handoff"]
    assert isinstance(compact_handoff, str)
    assert "## Route Steps" in compact_handoff
    assert "Step-by-Step Execution Guidance" not in compact_handoff
    assert "Quick Start for New Users" not in compact_handoff

    detailed_handoff = route_request("Plan a migration.", handoff_detail="detailed").to_dict()[
        "route_handoff"
    ]
    assert isinstance(detailed_handoff, str)
    assert "Step-by-Step Execution Guidance" in detailed_handoff
    assert "Quick Start for New Users" in detailed_handoff


def _mermaid_nodes_and_edges(
    route_handoff: str,
) -> tuple[set[str], list[tuple[str, str, str]], dict[str, str]]:
    block = route_handoff.split("```mermaid\n", 1)[1].split("\n```", 1)[0]
    nodes: set[str] = set()
    edges: list[tuple[str, str, str]] = []
    declarations: dict[str, str] = {}

    def node_id(raw: str) -> str:
        for separator in ("[", "{", "("):
            raw = raw.split(separator, 1)[0]
        return raw.strip()

    def record(raw: str) -> str:
        identifier = node_id(raw)
        nodes.add(identifier)
        declarations.setdefault(identifier, raw.strip())
        return identifier

    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("flowchart"):
            continue
        if "-->" in line:
            left, right = line.split("-->", 1)
            target = record(right)
            source = left.strip()
            label = ""
            if ' -- "' in left:
                source, label = left.split(' -- "', 1)
                source = source.strip()
                label = label.rstrip('"')
            source = record(source)
            edges.append((source, target, label))
        else:
            record(line)
    return nodes, edges, declarations


def test_mermaid_decision_branches_are_complete() -> None:
    cases = [
        (
            "Audit the repository and publish the accepted issues afterward.",
            "Publish Issues?",
        ),
        ("Use map-codebase, then plan-change, then implement-plan.", "Plan Approved?"),
        ("Implement the approved plan.", "Verification Passed?"),
    ]
    for request, decision_label in cases:
        decision = route_request(request).to_dict()
        route_handoff = decision["route_handoff"]
        assert isinstance(route_handoff, str)
        nodes, edges, declarations = _mermaid_nodes_and_edges(route_handoff)
        outgoing: dict[str, list[str]] = {}
        for source, target, _ in edges:
            outgoing.setdefault(source, []).append(target)
        decision_nodes = [node for node in nodes if node.startswith("Branch")]
        assert decision_nodes, route_handoff
        for node in decision_nodes:
            assert len(outgoing[node]) == 2, (node, outgoing[node], route_handoff)
            assert "?" in declarations[node], route_handoff
            assert len([edge for edge in edges if edge[1] == node]) == 1, (
                node,
                edges,
                route_handoff,
            )
        assert any(
            decision_label in declaration for declaration in declarations.values()
        ), route_handoff


def test_audit_publication_mermaid_routes_through_decision() -> None:
    decision = route_request(
        "Audit the repository and publish the accepted issues afterward."
    ).to_dict()
    route_handoff = decision["route_handoff"]
    assert isinstance(route_handoff, str)
    assert 'BranchPub1 -- "Yes" --> Step2["2. raise-issue' in route_handoff
    assert 'BranchPub1 -- "No" --> End' in route_handoff
    assert "Publish Issues?" in route_handoff


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Plan a fix.", False),
        ("Draft a refactor plan.", False),
        ("Plan the API change.", False),
        ("Create an implementation plan.", False),
        ("Brainstorm ways to change the resolver.", False),
        ("Brainstorm implementation approaches.", False),
        ("Fix the bug.", True),
        ("Please update the resolver.", True),
        ("Can you refactor this module?", True),
        ("Audit the repository and fix confirmed issues.", True),
        ("Plan the migration, then implement it.", True),
        ("After planning, execute the migration.", True),
        ("Implement the approved plan.", True),
        ("Fixing the bug would be nice.", False),
        ("Review the update list.", False),
        ("What is the best way to fix the resolver?", False),
        ("The patch is ready.", False),
    ],
    ids=lambda value: str(value)[:40],
)
def test_execution_requested_detects_intent_only(text: str, expected: bool) -> None:
    assert execution_requested(text) is expected


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_directory_link(link: Path, target: Path) -> bool:
    """Create a directory symlink, falling back to a Windows junction."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except OSError:
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and link.is_dir():
                    return True
            except OSError:
                pass
    return False


def test_cli_rejects_unsafe_handoff_destinations_without_writes(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    before = file_hashes(tmp_path)
    before.update(file_hashes(SKILL_ROOT))
    destinations = [
        ("--output-file", repository / "route-handoff.md"),
        ("--output-file", repository / "nested" / "route-handoff.md"),
        ("--output-file", SKILL_ROOT / "SKILL.md"),
        ("--output-file", SKILL_ROOT / "scripts" / "route_work.py"),
        ("--output-file", SKILL_ROOT / "nested" / "route-handoff.md"),
        ("--output-dir", repository),
        ("--output-dir", repository / "nested"),
        ("--output-dir", SKILL_ROOT),
    ]
    for flag, target in destinations:
        result = _run_cli(
            "--request",
            "Plan a fix.",
            "--repo-root",
            str(repository),
            flag,
            str(target),
        )
        assert result.returncode == 2, (flag, target, result.stderr)
        assert result.stdout == ""
        assert "outside the repository" in result.stderr, (flag, target)
    after = file_hashes(tmp_path)
    after.update(file_hashes(SKILL_ROOT))
    assert after == before


def test_cli_rejects_symlinked_handoff_destinations_resolving_into_protected_roots(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    link_repo = tmp_path / "link-repo"
    link_skill = tmp_path / "link-skill"
    if not _make_directory_link(link_repo, repository) or not _make_directory_link(
        link_skill, SKILL_ROOT
    ):
        pytest.skip("directory symlinks are not supported on this platform")
    before = file_hashes(tmp_path)
    before.update(file_hashes(SKILL_ROOT))
    for link in (link_repo, link_skill):
        result = _run_cli(
            "--request",
            "Plan a fix.",
            "--repo-root",
            str(repository),
            "--output-file",
            str(link / "route-handoff.md"),
        )
        assert result.returncode == 2, (link, result.stderr)
        assert "outside the repository" in result.stderr
    after = file_hashes(tmp_path)
    after.update(file_hashes(SKILL_ROOT))
    assert after == before


def test_handoff_destination_validator_accounts_for_symlinked_and_future_paths(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    protected = (canonical_path(repository), canonical_path(SKILL_ROOT))

    future_inside = handoff_destination(repository / "nested" / "route-handoff.md", None)
    assert future_inside is not None
    assert unsafe_handoff_root(future_inside, protected) == canonical_path(repository)

    future_skill = handoff_destination(SKILL_ROOT / "deep" / "route-handoff.md", None)
    assert future_skill is not None
    assert unsafe_handoff_root(future_skill, protected) == canonical_path(SKILL_ROOT)

    output_dir_inside = handoff_destination(None, repository / "nested")
    assert output_dir_inside is not None
    assert unsafe_handoff_root(output_dir_inside, protected) == canonical_path(repository)

    external = handoff_destination(tmp_path / "external" / "route-handoff.md", None)
    assert external is not None
    assert unsafe_handoff_root(external, protected) is None

    link = tmp_path / "link"
    if _make_directory_link(link, repository):
        via_link = handoff_destination(link / "route-handoff.md", None)
        assert via_link is not None
        assert unsafe_handoff_root(via_link, protected) == canonical_path(repository)


def test_cli_writes_handoff_outside_repository_and_skill(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    output_file = tmp_path / "external" / "route-handoff.md"
    result = _run_cli(
        "--request",
        "Fix the bug.",
        "--repo-root",
        str(repository),
        "--output-file",
        str(output_file),
    )
    assert result.returncode == 0, result.stderr
    assert output_file.is_file()
    assert "# Route Handoff Guidance" in output_file.read_text(encoding="utf-8")

    output_dir = tmp_path / "external-dir"
    output_dir.mkdir()
    result = _run_cli(
        "--request",
        "Fix the bug.",
        "--repo-root",
        str(repository),
        "--output-dir",
        str(output_dir),
    )
    assert result.returncode == 0, result.stderr
    assert (output_dir / "route-handoff.md").is_file()


def test_cli_rejects_handoff_output_inside_repository(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--request",
            "Plan a fix.",
            "--repo-root",
            str(repository),
            "--output-dir",
            str(repository / "docs"),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "outside the repository" in result.stderr


def test_cli_detailed_handoff_writes_file_on_request(tmp_path: Path) -> None:
    output_file = tmp_path / "route-handoff.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--request",
            "Brainstorm new feature ideas, design the architecture, and draft an implementation plan.",
            "--handoff",
            "detailed",
            "--output-file",
            str(output_file),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output_file.is_file()
    text = output_file.read_text(encoding="utf-8")
    assert "# Route Handoff Guidance" in text
    assert "```mermaid" in text
    assert "ideate" in text
    assert "design-codebase" in text
    assert "plan-change" in text
    assert "Step-by-Step Execution Guidance" in text
    assert "Quick Start for New Users" in text


def test_empty_request_fails_closed() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        route_request(" \n ")


def test_cli_reads_existing_request_and_facts_without_writing(tmp_path: Path) -> None:
    request = tmp_path / "request.txt"
    plan = tmp_path / "approved-plan.md"
    repository = tmp_path / "repository"
    repository.mkdir()
    request.write_text("Apply the requested change.", encoding="utf-8")
    plan.write_text("# Approved plan\n", encoding="utf-8")
    before = file_hashes(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--request-file",
            str(request),
            "--repo-root",
            str(repository),
            "--approved-plan",
            str(plan),
            "--issue-number",
            "42",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    decision = json.loads(result.stdout)
    assert decision["primary_skill"] == "implement-plan"
    jsonschema.validate(decision, SCHEMA)
    assert file_hashes(tmp_path) == before


def test_cli_writes_route_handoff_file(tmp_path: Path) -> None:
    output_file = tmp_path / "route-handoff.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--request",
            "Brainstorm new feature ideas, design the architecture, and draft an implementation plan.",
            "--output-file",
            str(output_file),
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output_file.is_file()
    text = output_file.read_text(encoding="utf-8")
    assert "# Route Handoff Guidance" in text
    assert "```mermaid" in text
    assert "ideate" in text
    assert "design-codebase" in text
    assert "plan-change" in text


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--request-file", "missing.txt"], "request file does not exist"),
        (["--request", "Plan a fix.", "--repo-root", "missing"], "repository root does not exist"),
        (
            ["--request", "Apply the change.", "--approved-plan", "missing.md"],
            "approved plan does not exist",
        ),
        (["--request", "Scope it.", "--issue-number", "0"], "issue number must be positive"),
        (["--request", " "], "request must not be empty"),
    ],
)
def test_cli_invalid_inputs_fail_without_a_decision(
    arguments: list[str],
    message: str,
) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr


def test_routing_policy_documents_every_router_skill() -> None:
    policy = (SKILL_ROOT / "references" / "routing-policy.md").read_text(encoding="utf-8")
    undocumented = [skill for skill in SKILLS if f"`{skill}`" not in policy]
    assert undocumented == []
