from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "implement-plan" / "scripts"

sys.path.insert(0, str(SCRIPTS))

import implementation_contract

RT = implementation_contract.plan_v7_runtime


def _init_repo(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)


def _seal_v7(repo: Path, request_path: Path, draft: str) -> str:
    draft_path = repo.parent / "draft.md"
    draft_path.write_text(draft, encoding="utf-8")
    return RT.seal_plan(repo, request_path, draft_path).text


def _build_sealed_text(body: str, proof: dict) -> str:
    receipt = (
        "<!-- plan-validation: 7; body-sha256: {}; proof-sha256: {} -->".format(
            RT._sha256(RT.canonical_body(body).encode("utf-8")),
            RT._sha256(RT._canonical_json(proof).encode("utf-8")),
        )
    )
    return body + "\n" + receipt + "\n" + "<!-- plan-proof: " + RT._canonical_json(proof) + " -->\n"


def test_implement_plan_accepts_current_v7_sealed_plan(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo, {"src/target.py": "def target(raw: str) -> str:\n    return raw.strip()\n"})
    request = tmp_path / "request.md"
    request.write_text("Handle absent target input.\n", encoding="utf-8")
    draft = """# Handle absent target input

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: an absent target input | when: target processes the value | then: it returns an empty string | unchanged: present values remain stripped

## Obligations
RQ-1: source: request | anchor: Handle absent target input | obligation: an absent target input must produce an empty string | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns absent-value handling

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | depends_on: none | change: return the empty string for absent values before stripping present names | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present input cases | when: the targeted target tests execute | then: absent input is empty and present input is stripped | command: python -m pytest tests/test_target.py -q
"""
    sealed = _seal_v7(repo, request, draft)
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    plan.write_text(sealed, encoding="utf-8")
    scaffolded = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "scaffold_implementation.py"),
            "--repo-root",
            str(repo),
            "--plan",
            str(plan),
            "--output",
            str(bundle),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["normalized"]["contract_version"] == 7
    assert value["warnings"] == []
    assert value["workspace"]["targets"][0]["path"] == "src/target.py"


def test_change_execution_order_follows_declared_dependencies(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(
        repo,
        {
            "src/core.py": "def normalize(raw: str) -> str:\n    return raw.strip()\n",
            "src/app.py": "def run(raw: str) -> str:\n    return normalize(raw)\n",
            "tests/test_target.py": "def test_target():\n    assert True\n",
        },
    )
    request = tmp_path / "request.md"
    request.write_text("Order the dependent changes.\n", encoding="utf-8")
    draft = """# Order the dependent changes

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: an input | when: app runs | then: it is normalized | unchanged: other behavior

## Obligations
RQ-1: source: request | anchor: Order the dependent changes | obligation: dependent changes must execute in declared dependency order | covered_by: SC-1, CH-1, CH-2

## Evidence
F-1: kind: source | path: src/core.py | lines: 1-2 | anchor: normalize | claim: normalize owns string normalization
F-2: kind: source | path: src/app.py | lines: 1-2 | anchor: run | claim: run delegates to normalize

## Implementation
CH-2: path: src/app.py | anchor: run | status: existing | evidence: F-2 | depends_on: CH-1 | change: route run through the normalized helper | locality: local | reversibility: reversible | propagation: local
CH-1: path: src/core.py | anchor: normalize | status: existing | evidence: F-1 | depends_on: none | change: harden the normalization seam before callers are routed through it | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: a normalized input | when: the targeted tests execute | then: app output is normalized | command: python -m pytest tests/test_target.py -q
"""
    sealed = _seal_v7(repo, request, draft)
    plan, diagnostics = implementation_contract.parse_plan(sealed)
    assert diagnostics == []
    assert plan is not None
    assert implementation_contract.change_execution_order(plan, version=7) == ["CH-1", "CH-2"]
    assert implementation_contract.change_execution_order(plan, version=6) == ["CH-2", "CH-1"]


@pytest.mark.parametrize("dependency", ["CH-2", "CH-99"], ids=["cycle", "missing"])
def test_intake_rejects_invalid_dependency_graph(tmp_path: Path, dependency: str) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo, {"src/target.py": "def target(raw: str) -> str:\n    return raw.strip()\n"})
    draft = """# Handle absent target input

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: an absent target input | when: target processes the value | then: it returns an empty string | unchanged: present values remain stripped

## Obligations
RQ-1: source: request | anchor: Handle absent target input | obligation: an absent target input must produce an empty string | covered_by: SC-1, CH-1, CH-2

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns absent-value handling

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | depends_on: {dependency} | change: return the empty string for absent values before stripping present names | locality: local | reversibility: reversible | propagation: local
CH-2: path: src/target.py | anchor: target | status: existing | evidence: F-1 | depends_on: CH-1 | change: harden the empty-string branch | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: absent and present input cases | when: the targeted target tests execute | then: absent input is empty and present input is stripped | command: python -m pytest tests/test_target.py -q
""".replace("""{dependency}""", dependency)
    proof = {
        "version": 7,
        "facts": [],
        "obligations": [],
        "binding": {
            "repository_id": str(repo.resolve()),
            "git_head": None,
            "request_sha256": "0" * 64,
            "plan_body_sha256": RT._sha256(RT.canonical_body(draft).encode("utf-8")),
            "files": [],
        },
    }
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(_build_sealed_text(draft, proof), encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    with pytest.raises(ValueError) as error:
        implementation_contract.scaffold_bundle(repo, plan_path, bundle, "run-1")
    assert "change.dependency" in str(error.value)


def test_intake_routes_unsupported_contract_back_to_plan_change(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo, {"src/target.py": "def target(raw: str) -> str:\n    return raw.strip()\n"})
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        "# Unsupported contract\n\n<!-- plan-contract: 8 -->\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle.json"
    with pytest.raises(ValueError) as error:
        implementation_contract.scaffold_bundle(repo, plan_path, bundle, "run-1")
    assert "contract.unsupported" in str(error.value)
