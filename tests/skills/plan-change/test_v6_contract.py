from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from .v6_helpers import (  # type: ignore[import-not-found]
    RUNTIME,
    SCRIPTS,
    generated_file_plan,
    high_risk_plan,
    make_repo,
    migration_plan,
    new_file_plan,
    tiny_plan,
)

PROOF_RE = RUNTIME.PROOF_RE
VALIDATION_RE = RUNTIME.VALIDATION_RE
canonical_body = RUNTIME.canonical_body
seal_plan = RUNTIME.seal_plan
validate_draft = RUNTIME.validate_draft
verify_sealed_plan = RUNTIME.verify_sealed_plan


def codes(result: Any) -> set[str]:
    return {item.code for item in result.diagnostics}


def test_v6_tiny_seals_with_generated_hashes_and_canonical_receipt(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")

    result = seal_plan(repo, request, draft)

    assert result.text.count("<!-- plan-proof:") == 1
    assert result.text.count("<!-- plan-validation: 6;") == 1
    assert "file-sha256" not in draft.read_text(encoding="utf-8")
    proof_match = PROOF_RE.search(result.text)
    assert proof_match is not None
    proof = json.loads(proof_match.group("json"))
    fact = proof["facts"][0]
    assert fact["file_sha256"] == hashlib.sha256((repo / "src" / "names.py").read_bytes()).hexdigest()
    assert fact["verified_kind"] == "source"
    plan, diagnostics, view = verify_sealed_plan(result.text, repo, request_bytes=request.read_bytes())
    assert diagnostics == []
    assert plan is not None and plan.tier == "tiny"
    assert view.opened_paths == ["src/names.py"]


def test_python_structured_fact_is_ast_verified_and_cached(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    result = validate_draft(tiny_plan(fact_kind="function-signature"), repo)
    assert result.valid
    assert result.fact_proofs[0]["verified_kind"] == "function-signature"
    assert result.view.opened_paths == ["src/names.py"]
    assert result.view.python_parse_count == 1
    assert result.view.hash_count == 1


def test_fabricated_structured_fact_is_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan(fact_kind="function-signature").replace("parameters: value", "parameters: tenant,value")
    result = validate_draft(draft, repo)
    assert "fact.structured" in codes(result)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda text: text.replace("lines: 1-2", "lines: 20-21"), "fact.lines"),
        (lambda text: text.replace("anchor: normalize_name", "anchor: missing", 1), "fact.anchor"),
        (lambda text: text.replace("path: src/names.py", "path: src/missing.py", 1), "fact.path"),
        (lambda text: text.replace("covers: SC-1, CH-1", "covers: SC-1"), "verification.coverage"),
        (lambda text: text.replace("## Evidence\n", "## Verification\n", 1), "section.order"),
    ],
)
def test_targeted_diagnostics(mutation, expected: str, tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert expected in codes(validate_draft(mutation(tiny_plan()), repo))


@pytest.mark.parametrize(
    "metadata",
    [
        '{"intent":"feature","tier":"tiny","risk_domains":["concurrency"]}',
        '{"intent":"feature","tier":"standard","risk_domains":["security"]}',
        '{"intent":"feature","tier":"high-risk","risk_domains":[]}',
        '{"intent":"unknown","tier":"tiny","risk_domains":[]}',
    ],
)
def test_metadata_contradictions_are_rejected(metadata: str, tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert "metadata.invalid" in codes(validate_draft(tiny_plan(metadata=metadata), repo))


def test_high_risk_boundary_and_risk_records_pass(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert validate_draft(high_risk_plan(), repo).valid


def test_new_file_requires_and_accepts_directory_owner(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert validate_draft(new_file_plan(), repo).valid
    invalid = new_file_plan().replace(" | owner: F-1", "")
    assert "change.target" in codes(validate_draft(invalid, repo))


def test_generated_output_owner_binds_only_the_generator(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "tools").mkdir()
    (repo / "tools" / "gen_names.py").write_text(
        "output = 'src/generated_names.py'\nother = 'src/other_names.py'; print('generated_names')\n",
        encoding="utf-8",
    )
    result = validate_draft(generated_file_plan(), repo)
    assert result.valid
    assert result.view.opened_paths == ["tools/gen_names.py"]
    assert result.view.hash_count == 1
    wrong_owner = generated_file_plan().replace(
        "output: src/generated_names.py",
        "output: src/other_names.py",
    )
    assert "change.evidence" in codes(validate_draft(wrong_owner, repo))


def test_high_risk_migration_requires_and_accepts_rollout(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert validate_draft(migration_plan(), repo).valid
    without_rollout = migration_plan().split("\n## Rollout and Rollback", 1)[0] + "\n"
    assert "section.order" in codes(validate_draft(without_rollout, repo))


def test_incomplete_consumer_plan_can_seal_for_quality_judging(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Refactor normalization and all affected consumers.\n", encoding="utf-8")
    draft.write_text(tiny_plan().replace('"tier":"tiny"', '"tier":"standard"'), encoding="utf-8")
    assert seal_plan(repo, request, draft).text.startswith("# Fix absent-name normalization")


def test_duplicate_and_undefined_references_are_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    duplicate = tiny_plan().replace("## Verification", "SC-1: given: duplicate record | when: parsed now | then: rejected now | unchanged: original remains\n\n## Verification")
    assert "record.invalid" in codes(validate_draft(duplicate, repo))
    undefined = tiny_plan().replace("covers: SC-1, CH-1", "covers: SC-9, CH-1")
    assert "reference.undefined" in codes(validate_draft(undefined, repo))


def test_bound_file_change_fails_but_unrelated_change_and_head_change_do_not(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", git=True)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    sealed = seal_plan(repo, request, draft).text
    (repo / "unrelated.md").write_text("noise\n", encoding="utf-8")
    subprocess.run(["git", "add", "unrelated.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "unrelated"], cwd=repo, check=True)
    assert verify_sealed_plan(sealed, repo)[1] == []
    source = repo / "src" / "names.py"
    source.write_text(source.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    assert "proof.stale" in {item.code for item in verify_sealed_plan(sealed, repo)[1]}


def test_tampered_body_and_proof_are_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    sealed = seal_plan(repo, request, draft).text
    assert "proof.stale" in {item.code for item in verify_sealed_plan(sealed.replace("empty string", "blank string", 1), repo)[1]}
    match = PROOF_RE.search(sealed)
    assert match is not None
    proof = json.loads(match.group("json"))
    proof["binding"]["request_sha256"] = "0" * 64
    tampered = sealed[: match.start("json")] + json.dumps(proof, sort_keys=True, separators=(",", ":")) + sealed[match.end("json") :]
    assert "proof.stale" in {item.code for item in verify_sealed_plan(tampered, repo)[1]}


def _rewrite_receipt(text: str, proof: dict[str, Any]) -> str:
    proof_match = PROOF_RE.search(text)
    assert proof_match is not None
    proof_json = json.dumps(proof, sort_keys=True, separators=(",", ":"))
    updated = text[: proof_match.start("json")] + proof_json + text[proof_match.end("json") :]
    receipt_match = VALIDATION_RE.search(updated)
    assert receipt_match is not None
    receipt = (
        "<!-- plan-validation: 6; body-sha256: "
        + hashlib.sha256(canonical_body(updated).encode()).hexdigest()
        + "; proof-sha256: "
        + hashlib.sha256(proof_json.encode()).hexdigest()
        + " -->"
    )
    return updated[: receipt_match.start()] + receipt + updated[receipt_match.end() :]


def test_recomputed_receipt_cannot_remove_derived_proof_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    sealed = seal_plan(repo, request, draft).text
    proof_match = PROOF_RE.search(sealed)
    assert proof_match is not None
    proof = json.loads(proof_match.group("json"))
    proof["facts"] = []
    proof["binding"]["files"] = []

    forged = _rewrite_receipt(sealed, proof)

    plan, diagnostics, view = verify_sealed_plan(forged, repo)
    assert plan is not None
    assert "proof.stale" in {item.code for item in diagnostics}
    assert view.opened_paths == ["src/names.py"]


def test_recomputed_receipt_cannot_hide_invalid_plan_semantics(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    sealed = seal_plan(repo, request, draft).text
    changed = sealed.replace("covers: SC-1, CH-1", "covers: SC-1")
    proof_match = PROOF_RE.search(changed)
    assert proof_match is not None
    proof = json.loads(proof_match.group("json"))
    proof["binding"]["plan_body_sha256"] = hashlib.sha256(canonical_body(changed).encode()).hexdigest()

    forged = _rewrite_receipt(changed, proof)

    assert "verification.coverage" in {item.code for item in verify_sealed_plan(forged, repo)[1]}


def _javascript_call_plan() -> str:
    return """# Update JavaScript name delegation

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"refactor","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: a JavaScript name caller | when: caller delegates normalization | then: callee supplies the normalized value | unchanged: caller return behavior remains stable

## Evidence
F-1: kind: call-edge | path: src/names.js | lines: 1-4 | anchor: caller | claim: caller delegates to callee | caller: caller | callee: callee

## Implementation
CH-1: path: src/names.js | anchor: caller | status: existing | evidence: F-1 | change: preserve the direct callee delegation while reorganizing the surrounding name module | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: a JavaScript name input | when: targeted JavaScript tests execute | then: caller returns the callee result | command: npm test -- names
"""


def test_tree_sitter_rejects_identifiers_that_exist_only_in_a_comment(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_javascript")
    repo = make_repo(tmp_path / "repo")
    source = repo / "src" / "names.js"
    source.write_text("function caller() {\n  // callee()\n  return 1;\n}\n", encoding="utf-8")
    assert "fact.structured" in codes(validate_draft(_javascript_call_plan(), repo))

    source.write_text("function caller() {\n  return callee();\n}\n\n", encoding="utf-8")
    result = validate_draft(_javascript_call_plan(), repo)
    assert result.valid
    assert result.fact_proofs[0]["verified_kind"] == "call-edge"


def test_new_change_ownership_cycles_are_rejected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = """# Add mutually dependent name modules

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: two new name modules | when: the package imports them | then: both modules expose their declared behavior | unchanged: existing normalization remains stable

## Evidence
F-1: kind: directory-ownership | path: src/__init__.py | lines: 1-1 | anchor: package | claim: src owns name modules | directory: src

## Implementation
CH-1: path: src/first.py | anchor: first module seam | status: new | owner: CH-2 | change: add the first concrete name module with an explicit package-facing entry point | locality: shared | reversibility: reversible
CH-2: path: src/second.py | anchor: second module seam | status: new | owner: CH-1 | change: add the second concrete name module with an explicit package-facing entry point | locality: shared | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: both new modules | when: targeted package tests execute | then: both imports expose the declared behavior | command: python -m pytest tests/test_names.py -q
"""
    assert "change.evidence" in codes(validate_draft(draft, repo))


def test_cli_emits_exact_markdown_or_canonical_json_diagnostics(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    command = [sys.executable, str(SCRIPTS / "seal_plan.py"), "--repo-root", str(repo), "--request-file", str(request), "--draft", str(draft)]
    success = subprocess.run(command, capture_output=True, text=True)
    assert success.returncode == 0 and success.stderr == ""
    assert success.stdout == seal_plan(repo, request, draft).text
    draft.write_text(tiny_plan().replace("anchor: normalize_name", "anchor: fabricated", 1), encoding="utf-8")
    failure = subprocess.run(command, capture_output=True, text=True)
    payload = json.loads(failure.stdout)
    assert failure.returncode == 1 and payload["valid"] is False
    assert payload["diagnostics"][0]["code"] == "fact.anchor"
    assert payload["diagnostics"][0]["record"] == "F-1"


def test_draft_rejects_manually_written_machine_markers(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("<!-- plan-metadata:", "<!-- plan-proof: {} -->\n<!-- plan-metadata:")
    assert "record.invalid" in codes(validate_draft(draft, repo))


def test_receipt_hashes_canonical_body_and_proof(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    sealed = seal_plan(repo, request, draft).text
    proof = PROOF_RE.search(sealed)
    receipt = VALIDATION_RE.search(sealed)
    assert proof is not None and receipt is not None
    assert receipt.group("body") == hashlib.sha256(canonical_body(sealed).encode()).hexdigest()
    assert receipt.group("proof") == hashlib.sha256(json.dumps(json.loads(proof.group("json")), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
