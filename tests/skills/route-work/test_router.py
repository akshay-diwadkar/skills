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
    route_request,
)


def load_cases(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
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
    assert "# Route Handoff Guidance" in first["route_handoff"]
    assert "```mermaid" in first["route_handoff"]
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
    assert "Direct Answer" in decision["route_handoff"]
    forbidden_actions = decision["forbidden_actions"]
    assert isinstance(forbidden_actions, list)
    assert "execute_selected_workflow" in forbidden_actions
    jsonschema.validate(decision, SCHEMA)


def test_normalization_is_stable() -> None:
    canonical = route_request("Plan a migration.").to_dict()
    assert route_request("  PLAN\u00a0a   migration.  ").to_dict() == canonical


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
            "Brainstorm new feature ideas, design architecture, and plan change.",
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
