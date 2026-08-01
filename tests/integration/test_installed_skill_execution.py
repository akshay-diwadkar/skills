from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_installed_plan_change_exposes_only_v6_sealer(tmp_path: Path) -> None:
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

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"refactor","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: a JavaScript caller | when: delegation executes | then: the callee result is returned | unchanged: direct delegation remains stable

## Evidence
F-1: kind: call-edge | path: src/names.js | lines: 1-4 | anchor: caller | claim: caller delegates to callee | caller: caller | callee: callee

## Implementation
CH-1: path: src/names.js | anchor: caller | status: existing | evidence: F-1 | change: preserve direct callee delegation while reorganizing the surrounding module implementation | locality: local | reversibility: reversible

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
    skill = ROOT / "skills" / "engineering" / "route-engineering-work"

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
            "scripts/route_engineering_work.py",
            "--request",
            "Use map-codebase, then plan-change, then implement-plan.",
        ],
        cwd=skill,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    decision = json.loads(result.stdout)
    assert decision["primary_skill"] == "plan-change"
    assert decision["prerequisites"] == ["map-codebase"]
    assert decision["follow_up"] == ["implement-plan"]
    assert decision["forbidden_actions"][-1] == "execute_selected_workflow"
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
        ("implement-plan", [f"plan_file={plan}"]),
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
        ("engineering", "route-engineering-work"),
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
        "audit-codebase": [f"request_file={existing}", f"bundle={existing}", f"checkpoint={tmp_path / 'checkpoint.json'}"],
        "optimize-codebase": [
            f"request_file={existing}",
            "path=full",
            "scope=targeted",
            "stage=plan",
            f"report={tmp_path / 'report.md'}",
            "implementation_authorized=no",
        ],
        "scope-issue": ["operation=execution-gate"],
        "diagram-codebase": [
            f"request_file={existing}",
            f"data={existing}",
            f"output={tmp_path / 'diagram.html'}",
            "create_dirs=no",
            "overwrite=no",
        ],
        "manualize": [
            f"request_file={existing}",
            "operation=audit",
            "profile=standard",
            f"manual={existing}",
            f"bundle={existing}",
            f"glossary={existing}",
        ],
        "route-engineering-work": ["request=Choose the planning workflow."],
    }
    argv = [
        sys.executable,
        str(installed / "scripts" / "cli.py"),
        "--repo-root",
        str(repo),
    ]
    if name != "route-engineering-work":
        argv.extend(["--run-dir", str(run)])
    for value in values[name]:
        argv.extend(["--input", value])
    argv.extend(["--format", "json", "doctor"])
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    response = json.loads(result.stdout)
    assert response["status"] == "ready"
    assert response["next_command"]["argv"][1] == str(installed / "scripts" / "cli.py")
    after = {
        path.relative_to(installed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert after == before


def test_installed_stateless_router_returns_inline_result_without_run_state(tmp_path: Path) -> None:
    source = ROOT / "skills" / "engineering" / "route-engineering-work"
    installed = tmp_path / "route-engineering-work"
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
            "request=Use map-codebase, then plan-change, then implement-plan.",
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
    assert response["result"]["primary_skill"] == "plan-change"
    assert response["result"]["prerequisites"] == ["map-codebase"]
    assert not list(tmp_path.rglob(".skill-cli-state.json"))
