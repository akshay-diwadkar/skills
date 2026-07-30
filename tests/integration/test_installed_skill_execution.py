from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_installed_plan_change_scaffold_is_v5(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "engineering" / "plan-change"
    result = subprocess.run(
        [sys.executable, "scripts/scaffold_plan.py", "--tier", "standard", "--intent", "feature"],
        cwd=skill,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "<!-- plan-contract: 5 -->" in result.stdout
    assert "Execution Blueprint:" in result.stdout


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
            [
                f"request_file={request}",
                "tier=tiny",
                "intent=bug-fix",
            ],
        ),
        ("implement-plan", [f"plan_file={plan}"]),
    ):
        source = ROOT / "skills" / "engineering" / name
        installed = tmp_path / "installed" / name
        shutil.copytree(source, installed)
        run = tmp_path / f"{name}-run"
        argv = [
            sys.executable,
            str(installed / "scripts" / "cli.py"),
            "--repo-root",
            str(repo),
            "--run-dir",
            str(run),
        ]
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
