from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_installed_plan_change_exposes_only_v7_sealer(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "engineering" / "plan-change"
    scripts = {path.name for path in (skill / "scripts").glob("*.py")}
    assert "seal_plan.py" in scripts
    assert not {"prepare_plan.py", "check_plan.py", "finalize_plan.py", "hash_excerpt.py", "plan_inventory.py", "scaffold_plan.py"} & scripts


def test_installed_plan_change_fails_closed_without_optional_tree_sitter(tmp_path: Path) -> None:
    source = ROOT / "skills" / "engineering" / "plan-change"
    installed = tmp_path / "installed" / "plan-change"
    shutil.copytree(source, installed)
    assert not (installed / "requirements.txt").exists()
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "names.js").write_text(
        "function caller() {\n  return callee();\n}\n\n", encoding="utf-8"
    )
    request = tmp_path / "request.md"
    request.write_text("Preserve JavaScript delegation.\n", encoding="utf-8")
    draft = tmp_path / "draft.md"
    plan = """# Preserve JavaScript delegation

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: a JavaScript caller | when: delegation executes | then: the callee result is returned | unchanged: direct delegation remains stable

## Obligations
RQ-1: source: request | anchor: Preserve JavaScript delegation | obligation: direct delegation must remain stable | covered_by: SC-1, CH-1

## Evidence
F-1: kind: call-edge | path: src/names.js | lines: 1-4 | anchor: caller | claim: caller delegates to callee | caller: caller | callee: callee

## Implementation
CH-1: path: src/names.js | anchor: caller | status: existing | evidence: F-1 | depends_on: none | change: preserve direct callee delegation while reorganizing the surrounding module implementation | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: a JavaScript input | when: targeted tests execute | then: caller returns the callee result | command: npm test -- names
"""
    draft.write_text(plan, encoding="utf-8")
    command = [
        sys.executable,
        "-S",
        str(installed / "scripts" / "seal_plan.py"),
        "--repo-root",
        str(repo),
        "--request-file",
        str(request),
        "--draft",
        str(draft),
    ]

    structured = subprocess.run(command, capture_output=True, text=True, check=False)

    assert structured.returncode == 1
    diagnostic = json.loads(structured.stdout)["diagnostics"][0]
    assert diagnostic["code"] == "fact.structured"
    assert diagnostic["record"] == "F-1"
    assert diagnostic["path"] == "src/names.js"
    assert "tree_sitter_javascript" in diagnostic["required_action"]

    draft.write_text(
        plan.replace("kind: call-edge", "kind: source").replace(" | caller: caller | callee: callee", ""),
        encoding="utf-8",
    )
    source_result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert source_result.returncode == 0, source_result.stdout + source_result.stderr
    assert '"verified_kind":"source"' in source_result.stdout


def test_installed_manualize_language_cli_executes(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "technical-communication" / "manualize"
    glossary = tmp_path / "glossary.json"
    manual = tmp_path / "manual.md"
    glossary.write_text(json.dumps({"terms": [], "abbreviations": {}}), encoding="utf-8")
    manual.write_text("# Procedure\n\nRun the service.\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_manual_language.py",
            "--profile",
            "strict",
            "--glossary",
            str(glossary),
            str(manual),
        ],
        cwd=skill,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["violations"] == []


def test_installed_router_executes_read_only(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "routing" / "route-work"

    def snapshot() -> dict[str, str]:
        return {
            path.relative_to(skill).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(skill.rglob("*"))
            if path.is_file()
        }

    before = snapshot()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/route_work.py",
            "--selected-skill",
            "map-codebase",
            "--selected-skill",
            "plan-change",
            "--selected-skill",
            "implement-plan",
            "--approved-plan-available",
            "true",
        ],
        cwd=skill,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    decision = json.loads(result.stdout)
    assert decision["valid"] is True
    assert decision["workflow"] == ["map-codebase", "plan-change", "implement-plan"]
    assert decision["errors"] == []
    assert snapshot() == before


def test_core_skill_clis_use_packaged_runtime_when_installed_alone(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    plan = tmp_path / "plan.md"
    plan.write_text("placeholder", encoding="utf-8")
    request = tmp_path / "request.md"
    request.write_text("Plan a local change.", encoding="utf-8")

    for name, inputs in (
        (
            "plan-change",
            [f"request_file={request}", f"draft_file={plan}"],
        ),
        ("implement-plan", [f"plan_file={plan}", f"bundle={plan}"]),
    ):
        source = ROOT / "skills" / "engineering" / name
        installed = tmp_path / "installed" / name
        shutil.copytree(source, installed)
        argv = [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
        ]
        if name != "plan-change":
            run = tmp_path / f"{name}-run"
            argv.extend(["--run-dir", str(run)])
        for value in inputs:
            argv.extend(["--input", value])
        argv.extend(["--format", "json", "doctor"])
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        response = json.loads(result.stdout)
        assert response["status"] == "ready"
        assert response["next_command"]["argv"][1] == str(installed / "scripts" / "cli.py")

        mismatch = subprocess.run(
            [
                sys.executable,
                str(installed / "scripts" / "cli.py"),
                "--skill-dir",
                str(repo),
                "--repo-root",
                str(repo),
                "--format",
                "json",
                "doctor",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert mismatch.returncode == 2
        assert json.loads(mismatch.stdout)["blocking_reasons"] == ["skill.adapter_mismatch"]


@pytest.mark.parametrize(
    ("domain", "name"),
    [
        ("engineering", "map-codebase"),
        ("engineering", "design-codebase"),
        ("engineering", "audit-codebase"),
        ("engineering", "optimize-codebase"),
        ("engineering", "scope-issue"),
        ("engineering", "diagram-codebase"),
        ("technical-communication", "manualize"),
        ("routing", "route-work"),
    ],
)
def test_remaining_skill_common_cli_runs_from_standalone_install(
    tmp_path: Path,
    domain: str,
    name: str,
) -> None:
    source = ROOT / "skills" / domain / name
    installed = tmp_path / "installed" / name
    shutil.copytree(source, installed)
    before = {
        path.relative_to(installed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    repo = tmp_path / "repo"
    repo.mkdir()
    existing = tmp_path / "input.json"
    existing.write_text("{}\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    run = tmp_path / f"{name}-run"
    values: dict[str, list[str]] = {
        "map-codebase": ["task=locate the application entrypoint"],
        "design-codebase": [f"draft={existing}", f"output_dir={output_dir}"],
        "audit-codebase": [f"bundle={existing}"],
        "optimize-codebase": [
            "scope=targeted",
            f"draft={existing}",
            f"output_dir={output_dir}",
        ],
        "scope-issue": [f"issue_json={existing}", f"draft={existing}", f"output_dir={output_dir}"],
        "diagram-codebase": [
            f"data={existing}",
            f"output={tmp_path / 'diagram.html'}",
            "create_dirs=no",
            "overwrite=no",
        ],
        "manualize": [
            "operation=audit",
            "profile=standard",
            f"manual={existing}",
            f"bundle={existing}",
            f"glossary={existing}",
        ],
        "route-work": ["selected_skills=plan-change"],
    }
    argv = [
        sys.executable,
        str(installed / "scripts" / "cli.py"),
        "--repo-root",
        str(repo),
    ]
    if name != "route-work":
        argv.extend(["--run-dir", str(run)])
    for value in values[name]:
        argv.extend(["--input", value])
    argv.extend(["--format", "json", "doctor"])
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "ready"
    if response["next_command"] is not None:
        assert response["next_command"]["argv"][1] == str(installed / "scripts" / "cli.py")
    after = {
        path.relative_to(installed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert after == before


def test_installed_stateless_router_returns_inline_result_without_run_state(tmp_path: Path) -> None:
    source = ROOT / "skills" / "routing" / "route-work"
    installed = tmp_path / "route-work"
    shutil.copytree(source, installed)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=plan-change",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "complete"
    assert response["result"]["valid"] is True
    assert response["result"]["workflow"] == ["plan-change"]
    assert not list(tmp_path.rglob(".skill-cli-state.json"))


def test_installed_stateless_router_persists_handoff_on_request(tmp_path: Path) -> None:
    source = ROOT / "skills" / "routing" / "route-work"
    installed = tmp_path / "route-work"
    shutil.copytree(source, installed)
    repo = tmp_path / "repo"
    repo.mkdir()
    handoff = tmp_path / "route-handoff.md"
    before = {
        path.relative_to(installed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    result = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=plan-change",
            "--input",
            f"handoff_output={handoff}",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "complete"
    assert handoff.is_file()
    assert "# Route Handoff Guidance" in handoff.read_text(encoding="utf-8")
    # Persisting on request must not modify the installed skill package.
    after = {
        path.relative_to(installed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert after == before


def test_installed_router_protocol_facts_affect_routing(tmp_path: Path) -> None:
    source = ROOT / "skills" / "routing" / "route-work"
    installed = tmp_path / "route-work"
    shutil.copytree(source, installed)
    repo = tmp_path / "repo"
    repo.mkdir()

    approved = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=implement-plan",
            "--input",
            "approved_plan_available=true",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert approved.returncode == 0, approved.stdout + approved.stderr
    response = json.loads(approved.stdout)
    assert response["status"] == "complete"
    assert response["result"]["valid"] is True
    assert response["result"]["workflow"] == ["implement-plan"]

    issue = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=scope-issue",
            "--input",
            "issue_context_available=true",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert issue.returncode == 0, issue.stdout + issue.stderr
    response = json.loads(issue.stdout)
    assert response["status"] == "complete"
    assert response["result"]["valid"] is True
    assert response["result"]["workflow"] == ["scope-issue"]

    without_facts = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=implement-plan",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert without_facts.returncode == 0, without_facts.stdout + without_facts.stderr
    response = json.loads(without_facts.stdout)
    assert response["result"]["valid"] is False
    assert [error["code"] for error in response["result"]["errors"]] == [
        "dependency.missing_artifact",
        "gate.approval_required",
    ]


@pytest.mark.parametrize(
    "target",
    [
        "<repo>/route-handoff.md",
        "<repo>/nested/route-handoff.md",
        "<installed>/SKILL.md",
        "<installed>/scripts/route_work.py",
        "<installed>/nested/route-handoff.md",
    ],
    ids=lambda value: value.replace("<", "").replace(">", "").replace("/", "-"),
)
def test_installed_router_rejects_handoff_output_inside_repo_or_skill(
    tmp_path: Path,
    target: str,
) -> None:
    source = ROOT / "skills" / "routing" / "route-work"
    installed = tmp_path / "route-work"
    shutil.copytree(source, installed)
    repo = tmp_path / "repo"
    repo.mkdir()
    destination = Path(
        target.replace("<repo>", str(repo)).replace("<installed>", str(installed))
    )

    def snapshot(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }

    before_repo = snapshot(repo)
    before_skill = snapshot(installed)
    result = subprocess.run(
        [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--input",
            "selected_skills=plan-change",
            "--input",
            f"handoff_output={destination}",
            "--format",
            "json",
            "run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3, (target, result.stdout, result.stderr)
    response = json.loads(result.stdout)
    assert response["status"] == "blocked"
    assert "handoff output must be outside the repository and installed skill" in response[
        "diagnostics"
    ][0]["message"]
    assert snapshot(repo) == before_repo
    assert snapshot(installed) == before_skill
