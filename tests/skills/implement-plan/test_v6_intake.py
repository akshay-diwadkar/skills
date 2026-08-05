from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEALER = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "seal_plan.py"
SCAFFOLD = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "scaffold_implementation.py"
FINALIZER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "seal_implementation.py"
SCRIPTS = ROOT / "skills" / "engineering" / "implement-plan" / "scripts"


def _git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)


def _passed_verification(*t_ids: str, command: str = "python -m pytest -q") -> dict:
    return {
        "t_ids": list(t_ids),
        "command": command,
        "expected": "pass",
        "exit_code": 0,
        "status": "passed",
        "evidence": "targeted verification passed",
    }


def _mark_complete(value: dict, *, ch_ids: list[str], paths: list[str], anchors: list[str], t_ids: list[str]) -> None:
    before = {
        path: next(
            target["before_sha256"]
            for target in value["workspace"]["targets"]
            if target["path"] == path
        )
        for path in paths
    }
    value["changes"] = [
        {
            "kind": "planned",
            "ch_ids": ch_ids,
            "paths": paths,
            "anchors": anchors,
            "before_sha256": before,
            "after_sha256": before,
            "evidence": [f"F-{index}" for index in range(1, len(ch_ids) + 1)],
            "verification": t_ids,
        }
    ]
    value["verification"] = [_passed_verification(*t_ids)]
    value["unresolved_changes"] = []
    value["unresolved_tests"] = []


def _seal_v7(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "target.py").write_text(
        "def target(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8"
    )
    _git_repo(repo)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    plan = tmp_path / "plan.md"
    request.write_text("Handle empty target input.\n", encoding="utf-8")
    draft.write_text(
        """# Handle empty target input

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: empty target input | obligation: return an empty string for empty target input | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an empty target input | when: target processes the value | then: it returns an empty string | unchanged: non-empty values remain stripped

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: return an empty string explicitly before stripping non-empty input values | depends_on: none | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: empty and non-empty values | when: targeted target tests execute | then: the case fails before the fix and passes after the fix with empty input empty while non-empty input is stripped | command: python -m pytest tests/test_target.py -q
""",
        encoding="utf-8",
    )
    sealed = subprocess.run(
        [sys.executable, str(SEALER), "--repo-root", str(repo), "--request-file", str(request), "--draft", str(draft)],
        capture_output=True,
        text=True,
        check=True,
    )
    plan.write_text(sealed.stdout, encoding="utf-8")
    return repo, plan, request


def test_v7_plan_scaffolds_and_seals_end_to_end(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["contract_version"] == 7
    assert value["plan"]["change_order"] == ["CH-1"]
    _mark_complete(
        value,
        ch_ids=["CH-1"],
        paths=["src/target.py"],
        anchors=["target"],
        t_ids=["T-1"],
    )
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    finalized = subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--plan",
            str(plan),
            "--bundle",
            str(bundle),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode == 0, finalized.stdout + finalized.stderr
    sealed_bundle = json.loads(bundle.read_text(encoding="utf-8"))
    assert sealed_bundle["status"] == "complete"
    assert sealed_bundle["validation_receipt"]["plan_contract"] == 7
    assert sealed_bundle["validation_receipt"]["implementation_contract"] == 4


def test_v7_receipt_records_plan_contract_7(tmp_path: Path) -> None:
    test_v7_plan_scaffolds_and_seals_end_to_end(tmp_path)


def test_unsupported_plan_version_fails_locally(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "target.py").write_text("x = 1\n", encoding="utf-8")
    _git_repo(repo)
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    plan.write_text(
        """# Bad

<!-- plan-contract: 5 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: a | when: b | then: c | unchanged: d
""",
        encoding="utf-8",
    )
    bundle.write_text("{}\n", encoding="utf-8")
    finalized = subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--plan",
            str(plan),
            "--bundle",
            str(bundle),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode != 0
    assert "unsupported" in (finalized.stdout + finalized.stderr).lower()


def test_v7_out_of_order_completion_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "a.py").write_text("A = 1\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
    _git_repo(repo)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    request.write_text("Add ordered modules a then b.\n", encoding="utf-8")
    draft.write_text(
        """# Add ordered modules

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: ordered modules | obligation: add module a before module b | covered_by: SC-1, CH-1, CH-2, T-1

## Outcome
SC-1: given: both modules | when: imports resolve | then: both expose constants | unchanged: unrelated packages remain untouched

## Evidence
F-1: kind: source | path: src/a.py | lines: 1-1 | anchor: A | claim: a module owns the first constant
F-2: kind: source | path: src/b.py | lines: 1-1 | anchor: B | claim: b module owns the second constant

## Implementation
CH-1: path: src/a.py | anchor: A | status: existing | evidence: F-1 | change: keep module a constant definition as the first ordered seam | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/b.py | anchor: B | status: existing | evidence: F-2 | change: keep module b constant definition as the second ordered seam | depends_on: CH-1 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: test | disposition: test-only | path: tests | owner: CH-1 | reason: F-1 ordered module a needs distinct test coverage surface
P-2: surface: test | disposition: out-of-scope | path: src/a.py | owner: CH-2 | reason: F-2 bounded sweep found no extra consumers beyond ordered module b

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: both modules | when: imports execute | then: both constants resolve | command: python -c "import src.a, src.b"
""",
        encoding="utf-8",
    )
    # Fix P-2 - tests path may not work. Use tests/ as directory - repository.get might fail.
    # Use a real file for test path.
    (repo / "tests" / "test_order.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    draft.write_text(
        draft.read_text(encoding="utf-8").replace(
            "path: tests | owner: CH-1",
            "path: tests/test_order.py | owner: CH-1",
        ),
        encoding="utf-8",
    )
    sealed = subprocess.run(
        [sys.executable, str(SEALER), "--repo-root", str(repo), "--request-file", str(request), "--draft", str(draft)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sealed.returncode == 0, sealed.stdout + sealed.stderr
    plan.write_text(sealed.stdout, encoding="utf-8")
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["change_order"] == ["CH-1", "CH-2"]
    value["changes"] = [
        {
            "kind": "planned",
            "ch_ids": ["CH-2"],
            "paths": ["src/b.py"],
            "anchors": ["B"],
            "before_sha256": {"src/b.py": ""},
            "after_sha256": {"src/b.py": ""},
            "evidence": ["F-2"],
            "verification": ["T-1"],
        }
    ]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    finalized = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode != 0
    assert "before prerequisites" in finalized.stdout


def test_v6_plan_scaffolds_and_seals_end_to_end(tmp_path: Path) -> None:
    sys.path.insert(0, str(SCRIPTS))
    import plan_v6_runtime as v6

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "target.py").write_text(
        "def target(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8"
    )
    _git_repo(repo)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    request.write_text("Handle empty target input.\n", encoding="utf-8")
    draft.write_text(
        """# Handle empty target input

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: an empty target input | when: target processes the value | then: it returns an empty string | unchanged: non-empty values remain stripped

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: return an empty string explicitly before stripping non-empty input values

## Verification
T-1: covers: SC-1, CH-1 | given: empty and non-empty values | when: targeted tests execute | then: empty input is empty and non-empty input is stripped | command: python -m pytest tests/test_target.py -q
""",
        encoding="utf-8",
    )
    sealed = v6.seal_plan(repo, request, draft)
    plan.write_text(sealed.text, encoding="utf-8")
    assert "plan-contract: 6" in sealed.text
    assert "RQ-" not in sealed.text.split("## Outcome", 1)[0]
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["contract_version"] == 6
    assert value["plan"]["change_order"] == ["CH-1"]
    assert value["workspace"]["targets"][0]["depends_on"] == "none"
    _mark_complete(
        value,
        ch_ids=["CH-1"],
        paths=["src/target.py"],
        anchors=["target"],
        t_ids=["T-1"],
    )
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    finalized = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode == 0, finalized.stdout + finalized.stderr
    sealed_bundle = json.loads(bundle.read_text(encoding="utf-8"))
    assert sealed_bundle["validation_receipt"]["plan_contract"] == 6
    assert sealed_bundle["validation_receipt"]["implementation_contract"] == 4


def test_v7_change_order_tamper_fails(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert scaffolded.returncode == 0
    value = json.loads(bundle.read_text(encoding="utf-8"))
    value["plan"]["change_order"] = []
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    finalized = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode != 0
    assert "change_order" in finalized.stdout


def test_v7_empty_changes_fail_completion(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        check=True,
        capture_output=True,
        text=True,
    )
    finalized = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode != 0
    assert "exactly once" in finalized.stdout


def test_v7_duplicate_and_unknown_ch_fail(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(bundle.read_text(encoding="utf-8"))
    sha = value["workspace"]["targets"][0]["before_sha256"]
    value["changes"] = [
        {
            "kind": "planned",
            "ch_ids": ["CH-1", "CH-1"],
            "paths": ["src/target.py"],
            "anchors": ["target"],
            "before_sha256": {"src/target.py": sha},
            "after_sha256": {"src/target.py": sha},
            "evidence": ["F-1"],
            "verification": ["T-1"],
        }
    ]
    value["verification"] = [_passed_verification("T-1")]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    duplicate = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert duplicate.returncode != 0
    assert "exactly once" in duplicate.stdout
    value["changes"][0]["ch_ids"] = ["CH-9"]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    unknown = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert unknown.returncode != 0
    assert "unknown CH" in unknown.stdout


def test_v7_independent_changes_any_valid_topo_order_seals(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "a.py").write_text("A = 1\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("B = 1\n", encoding="utf-8")
    (repo / "tests" / "test_order.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _git_repo(repo)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    request.write_text("Add independent modules a and b.\n", encoding="utf-8")
    draft.write_text(
        """# Add independent modules

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: independent modules | obligation: add modules a and b independently | covered_by: SC-1, CH-1, CH-2, T-1

## Outcome
SC-1: given: both modules | when: imports resolve | then: both expose constants | unchanged: unrelated packages remain untouched

## Evidence
F-1: kind: source | path: src/a.py | lines: 1-1 | anchor: A | claim: a module owns the first constant
F-2: kind: source | path: src/b.py | lines: 1-1 | anchor: B | claim: b module owns the second constant

## Implementation
CH-1: path: src/a.py | anchor: A | status: existing | evidence: F-1 | change: keep module a constant definition | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/b.py | anchor: B | status: existing | evidence: F-2 | change: keep module b constant definition | depends_on: none | locality: shared | reversibility: reversible

## Propagation
P-1: surface: test | disposition: test-only | path: tests/test_order.py | owner: CH-1 | reason: F-1 module a needs distinct test coverage surface
P-2: surface: test | disposition: out-of-scope | path: src/a.py | owner: CH-2 | reason: F-2 bounded sweep found no extra consumers beyond module b

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: both modules | when: imports execute | then: both constants resolve | command: python -c "import src.a, src.b"
""",
        encoding="utf-8",
    )
    sealed = subprocess.run(
        [sys.executable, str(SEALER), "--repo-root", str(repo), "--request-file", str(request), "--draft", str(draft)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert sealed.returncode == 0, sealed.stdout + sealed.stderr
    plan.write_text(sealed.stdout, encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["change_order"] == ["CH-1", "CH-2"]
    sha_a = next(t["before_sha256"] for t in value["workspace"]["targets"] if t["ch_id"] == "CH-1")
    sha_b = next(t["before_sha256"] for t in value["workspace"]["targets"] if t["ch_id"] == "CH-2")
    value["changes"] = [
        {
            "kind": "planned",
            "ch_ids": ["CH-2"],
            "paths": ["src/b.py"],
            "anchors": ["B"],
            "before_sha256": {"src/b.py": sha_b},
            "after_sha256": {"src/b.py": sha_b},
            "evidence": ["F-2"],
            "verification": ["T-1"],
        },
        {
            "kind": "planned",
            "ch_ids": ["CH-1"],
            "paths": ["src/a.py"],
            "anchors": ["A"],
            "before_sha256": {"src/a.py": sha_a},
            "after_sha256": {"src/a.py": sha_a},
            "evidence": ["F-1"],
            "verification": ["T-1"],
        },
    ]
    value["verification"] = [_passed_verification("T-1")]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    finalized = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode == 0, finalized.stdout + finalized.stderr
    assert json.loads(bundle.read_text(encoding="utf-8"))["status"] == "complete"


def test_v7_missing_or_failed_verification_fails(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(bundle.read_text(encoding="utf-8"))
    _mark_complete(
        value,
        ch_ids=["CH-1"],
        paths=["src/target.py"],
        anchors=["target"],
        t_ids=["T-1"],
    )
    value["verification"] = []
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    missing = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "planned T must appear in a passed verification row" in missing.stdout
    value["verification"] = [
        {
            "t_ids": ["T-1"],
            "command": "python -m pytest -q",
            "expected": "pass",
            "exit_code": 1,
            "status": "failed",
            "evidence": "failed",
        }
    ]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode != 0
    assert "planned T must appear in a passed verification row" in failed.stdout


def test_v7_unresolved_work_fails(tmp_path: Path) -> None:
    repo, plan, _request = _seal_v7(tmp_path)
    bundle = tmp_path / "bundle.json"
    subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(bundle.read_text(encoding="utf-8"))
    _mark_complete(
        value,
        ch_ids=["CH-1"],
        paths=["src/target.py"],
        anchors=["target"],
        t_ids=["T-1"],
    )
    value["unresolved_changes"] = ["CH-1"]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    changes = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert changes.returncode != 0
    assert "unresolved_changes must be empty" in changes.stdout
    value["unresolved_changes"] = []
    value["unresolved_tests"] = ["T-1"]
    bundle.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    tests = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan), "--bundle", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert tests.returncode != 0
    assert "unresolved_tests must be empty" in tests.stdout
