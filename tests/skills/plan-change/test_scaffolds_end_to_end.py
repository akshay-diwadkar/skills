from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import finalized_text, validate_plan  # noqa: E402

SPEC = importlib.util.spec_from_file_location("plan_scaffold_contract", SCRIPTS / "plan_contract.py")
assert SPEC and SPEC.loader
SCAFFOLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAFFOLD)


def _hydrated(tmp_path: Path, tier: str, domains: list[str]) -> str:
    (tmp_path / "src").mkdir(exist_ok=True)
    source = "def target(raw: str) -> str:\n    return raw.strip()\n"
    path = tmp_path / "src" / "target.py"
    path.write_text(source, encoding="utf-8")
    excerpt = "def target(raw: str) -> str:\n"
    text = SCAFFOLD.render_scaffold(tier, "bug-fix", domains)
    replacements = {
        "REPLACE_CURRENT_PATH": "src/target.py",
        "REPLACE_CURRENT_RANGE": "1-1",
        "REPLACE_CURRENT_ANCHOR": "target",
        "REPLACE_CURRENT_HASH": hashlib.sha256(excerpt.encode()).hexdigest(),
        "REPLACE_CURRENT_FILE_HASH": hashlib.sha256(path.read_bytes()).hexdigest(),
        "REPLACE_EXACT_SIGNATURE": "raw: str",
        "REPLACE_EXACT_RETURN": "str",
        "REPLACE_TARGETED_TEST.py": "test_target.py",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    for domain in domains:
        text = text.replace(f"REPLACE_{domain}.py", f"test_{domain}.py")
    return text


@pytest.mark.parametrize(
    ("tier", "domains"),
    [
        ("tiny", []),
        ("standard", []),
        *[("high-risk", [domain]) for domain in sorted(SCAFFOLD.RISK_DOMAINS)],
        ("high-risk", ["public-contract", "durable-state"]),
        ("high-risk", ["security", "public-contract", "migration"]),
        ("high-risk", ["concurrency", "external-integration", "irreversible-external-effect"]),
    ],
)
def test_hydrated_scaffolds_validate_and_finalize(tmp_path: Path, tier: str, domains: list[str]) -> None:
    draft = _hydrated(tmp_path, tier, domains)
    _plan, diagnostics = validate_plan(draft, tmp_path)
    assert diagnostics == []
    finalized = finalized_text(draft, tmp_path)
    finalized_plan, diagnostics = validate_plan(finalized, tmp_path, require_finalized=True)
    assert diagnostics == []
    assert finalized_plan is not None and finalized_plan.binding is not None
    assert "branch" not in finalized_plan.binding


def test_high_risk_scaffold_requires_a_domain() -> None:
    with pytest.raises(ValueError, match="at least one risk domain"):
        SCAFFOLD.render_scaffold("high-risk", "feature", [])


def _fact_hashes(path: Path, start: int, end: int) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = "\n".join(lines[start - 1 : end]) + "\n"
    return hashlib.sha256(excerpt.encode()).hexdigest(), hashlib.sha256(path.read_bytes()).hexdigest()


def _language_plan(repo: Path, tier: str, anchor: str, inventory: dict[str, Any]) -> str:
    is_kotlin = repo.name.startswith("kotlin")
    tiny = tier == "tiny"
    primary_path = (
        "src/Names.kt"
        if tiny and is_kotlin
        else "src/names.ts"
        if tiny
        else "src/internal/Parser.kt"
        if is_kotlin
        else "src/parser.ts"
    )
    primary = repo / primary_path
    primary_lines = (1, 3) if tiny else (3, 5) if is_kotlin else (1, 3)
    primary_excerpt, primary_file = _fact_hashes(primary, *primary_lines)
    facts: list[str] = []
    if tiny:
        callee = "name!!.trim" if is_kotlin else "name.trim"
        facts.append(
            f"- F-1: kind: call-edge | path: {primary_path} | lines: {primary_lines[0]}-{primary_lines[1]} "
            f"| anchor: {anchor} | excerpt-sha256: {primary_excerpt} | file-sha256: {primary_file} "
            f"| observation: nullable input reaches an unconditional string normalization call | caller: {anchor} "
            f"| callee: {callee}"
        )
    else:
        parameters = "raw: String" if is_kotlin else "raw: string"
        returns = "String" if is_kotlin else "string"
        facts.append(
            f"- F-1: kind: function-signature | path: {primary_path} | lines: {primary_lines[0]}-{primary_lines[1]} "
            f"| anchor: {anchor} | excerpt-sha256: {primary_excerpt} | file-sha256: {primary_file} "
            f"| observation: parseValue is the shared definition reached through forwarding surfaces "
            f"| parameters: {parameters} | returns: {returns} | async: false"
        )
    candidates = list(inventory["candidates"])
    remaining = [candidate for candidate in candidates if candidate["path"] != primary_path]
    for index, candidate in enumerate(remaining, 2):
        path = repo / candidate["path"]
        lines = path.read_text(encoding="utf-8").splitlines()
        excerpt_hash, file_hash = _fact_hashes(path, 1, len(lines))
        facts.append(
            f"- F-{index}: kind: documentation-contract | path: {candidate['path']} | lines: 1-{len(lines)} "
            f"| anchor: parseValue | excerpt-sha256: {excerpt_hash} | file-sha256: {file_hash} "
            f"| observation: {candidate['surface']} references the shared parseValue contract"
        )
    metadata = {
        "provisional": {
            "intent": "bug-fix" if tiny else "refactor",
            "risk_domains": [],
            "tier": tier,
            "tier_signals": [] if tiny else ["transitive-consumers", "multiple-test-surfaces"],
        },
        "final": {
            "intent": "bug-fix" if tiny else "refactor",
            "risk_domains": [],
            "tier": tier,
            "tier_signals": [] if tiny else ["transitive-consumers", "multiple-test-surfaces"],
        },
    }
    changes: list[str] = []
    propagations: list[str] = []
    for index, candidate in enumerate(candidates, 1):
        fact_number = 1 if candidate["path"] == primary_path else remaining.index(candidate) + 2
        locality = "test-only" if candidate["surface"] == "fixture" else "local-production" if tiny else "shared-production"
        changes.append(
            f"- CH-{index}: path: {candidate['path']} | anchor: {anchor if candidate['path'] == primary_path else 'parseValue'} "
            f"| status: existing | locality: {locality} | reversibility: reversible | evidence: F-{fact_number} "
            f"| change: {'add a null branch before preserving trim and case normalization' if tiny else 'rename parseValue consistently while preserving input output errors ordering and side effects'}"
        )
        propagations.append(
            f"- P-{index}: owner: CH-{index} | because: F-{fact_number} | surface: {candidate['surface']} "
            "| disposition: changed"
        )
    change_ids = ", ".join(f"CH-{index}" for index in range(1, len(changes) + 1))
    rows = [
        f"# {'Handle nullable names' if tiny else 'Rename the shared parser contract'}",
        "<!-- plan-contract: 5 -->",
        "<!-- plan-metadata: " + json.dumps(metadata, separators=(",", ":")) + " -->",
        "",
        "## Outcome and Scope",
        (
            "- SC-1: given: a nullable name | when: normalizeName receives null | then: it returns an empty string "
            "| unchanged: non-null names remain trimmed and lowercased"
            if tiny
            else "- SC-1: given: parser callers use the public forwarding surface | when: parseValue is renamed "
            "| then: the definition re-export facade consumer and test use the new name | unchanged: trimming behavior remains identical"
        ),
        "",
        "## Evidence Ledger",
        *facts,
        "",
        "## Decisions",
        (
            "- D-1: selected: add one local null guard before normalization | evidence: F-1 "
            "| rejected: remove nullable input from the signature | drawback: null and empty names share one result"
            if tiny
            else "- D-1: selected: rename the definition and every forwarding consumer in one dependency-ordered change "
            "| evidence: F-1 | rejected: retain a compatibility alias indefinitely | drawback: all repository consumers change together"
        ),
    ]
    if not tiny:
        rows.append("- C-1: constraint: preserve parser trimming behavior across the rename | evidence: F-1")
    rows.extend(["", "## Implementation Specification", *changes])
    if not tiny:
        rows.extend(
            [
                "",
                f"### Execution Blueprint: {change_ids} \N{EM DASH} dependency-ordered rename [type: dependency-table; domains: none]",
                "| Order | Surface | Action |",
                "|---|---|---|",
                "| 1 | definition | rename while preserving the exact branch, error, ordering, and side effect behavior |",
                "| 2 | forwarding API | update the re-export or facade after the definition |",
                "| 3 | consumers and tests | update imports, calls, and exact expectations |",
            ]
        )
    rows.extend(
        [
            "",
            "## Propagation Record",
            *propagations,
            "",
            "## Boundary Traces",
            (
                "- B-1: class: nullable function input boundary | path: F-1 "
                "| flow: nullable caller input -> normalizeName null guard or normalization -> string result"
                if tiny
                else "- B-1: class: shared parser API boundary | path: F-1 "
                "| flow: CLI or test input -> forwarding export and parser definition -> trimmed string result"
            ),
            "",
            "## Domain Obligations",
            "",
            "## Traceability",
            "| Criterion / constraint | Changes | Tests |",
            "|---|---|---|",
            f"| SC-1 | {change_ids} | T-1 |",
        ]
    )
    if not tiny:
        rows.append(f"| C-1 | {change_ids} | T-1 |")
    rows.extend(
        [
            "",
            "## Verification",
            (
                "- T-1: given: null empty and padded mixed-case names | when: normalizeName runs "
                "| then: caller propagation returns empty for null and empty while non-null text is trimmed then lowercased with no side effect "
                "| command: npm test -- names"
                if tiny and not is_kotlin
                else "- T-1: given: null empty and padded mixed-case names | when: normalizeName runs "
                "| then: caller propagation returns empty for null and empty while non-null text is trimmed then lowercased with no side effect "
                "| command: ./gradlew test --tests NamesTest"
                if tiny
                else "- T-1: given: definition forwarding re-export or facade consumer and fixture references "
                "| when: the targeted parser tests run | then: propagation updates every caller and re-export while preserving "
                "boundary input literal implementation branch error ordering side effect and trimmed output "
                f"| command: {'./gradlew test --tests ParserTest' if is_kotlin else 'npm test -- parser'}"
            ),
            "",
            "## Risks, Assumptions, and Attack",
            f"- A-forgotten-propagation: status: repaired | finding: propagation could miss a caller consumer or re-export "
            f"| evidence: F-1 | resolution: {change_ids}, T-1",
            f"- A-boundary-input: status: repaired | finding: null empty or invalid boundary input could change behavior "
            f"| evidence: F-1 | resolution: {change_ids}, T-1",
            f"- A-literal-implementation: status: repaired | finding: literal implementation could alter branch ordering or side effect behavior "
            f"| evidence: F-1 | resolution: {change_ids}, T-1",
        ]
    )
    return "\n".join(rows) + "\n"


@pytest.mark.parametrize(
    ("fixture_name", "tier", "anchor", "request_text"),
    [
        ("typescript-tiny", "tiny", "normalizeName", "Fix normalizeName for absent names."),
        ("typescript-standard", "standard", "parseValue", "Rename parseValue across its re-export and consumers."),
        ("kotlin-tiny", "tiny", "normalizeName", "Fix normalizeName for null names."),
        ("kotlin-standard", "standard", "parseValue", "Rename parseValue across its public facade and consumers."),
    ],
)
def test_non_python_fixtures_prepare_check_finalize_from_arbitrary_cwd(
    tmp_path: Path, fixture_name: str, tier: str, anchor: str, request_text: str
) -> None:
    repo = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / fixture_name
    request = tmp_path / f"{fixture_name}-request.md"
    request.write_text(request_text, encoding="utf-8")
    run_dir = tmp_path / f"{fixture_name}-run"
    relative_anchor = next(
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*")
        if path.is_file() and anchor in path.read_text(encoding="utf-8")
    )
    prepare = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "prepare_plan.py"),
            "--repo-root",
            str(repo),
            "--request-file",
            str(request),
            "--run-dir",
            str(run_dir),
            "--tier",
            tier,
            "--intent",
            "bug-fix" if tier == "tiny" else "refactor",
            "--anchor",
            f"{relative_anchor}:{anchor}",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert prepare.returncode == 0, prepare.stderr
    inventory = json.loads((run_dir / "inventory.json").read_text(encoding="utf-8"))
    draft = _language_plan(repo, tier, anchor, inventory)
    draft_path = run_dir / "draft.md"
    draft_path.write_text(draft, encoding="utf-8")
    common = [
        "--tier",
        tier,
        "--repo-root",
        str(repo),
        "--baseline",
        str(run_dir / "baseline.json"),
        "--inventory",
        str(run_dir / "inventory.json"),
    ]
    checked = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_plan.py"), *common, "--format", "json", str(draft_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0, f"{checked.stdout}\n{checked.stderr}"
    finalized = subprocess.run(
        [sys.executable, str(SCRIPTS / "finalize_plan.py"), *common, str(draft_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert finalized.returncode == 0, finalized.stderr
    finalized_path = run_dir / "finalized.md"
    finalized_path.write_text(finalized.stdout, encoding="utf-8")
    receipt_check = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "check_plan.py"),
            *common,
            "--require-finalized",
            "--format",
            "json",
            str(finalized_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert receipt_check.returncode == 0, f"{receipt_check.stdout}\n{receipt_check.stderr}"
