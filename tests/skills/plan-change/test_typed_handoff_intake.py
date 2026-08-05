from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("typed_handoff_runtime", SCRIPTS / "plan_runtime.py")
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


def sealed(kind: str, body: str, version: int = 1) -> bytes:
    digest = hashlib.sha256(body.encode()).hexdigest()
    return f"<!-- {kind}-handoff: {version}; sha256: {digest} -->\n{body}".encode()


def _diagnostics(error: BaseException) -> tuple[Any, ...]:
    diagnostics = getattr(error, "diagnostics", None)
    assert isinstance(diagnostics, tuple)
    return diagnostics


@pytest.mark.parametrize(
    ("kind", "body"),
    [
        ("design", "# Design Handoff: Boundary\n"),
        ("optimization", "# Optimization\n- H-1: next: plan-ready | candidate: C-1\n"),
        ("issue", '<!-- issue-handoff-metadata -->\n```json\n{"status":"plan-ready"}\n```\n'),
    ],
)
def test_detects_actionable_typed_handoffs(kind: str, body: str) -> None:
    assert RUNTIME.detect_request_source(sealed(kind, body)) == {"kind": kind, "contract_version": 1, "item": None}


def test_audit_requires_one_selected_finding_when_multiple() -> None:
    body = "# Audit Issue Handoff\n## Issue A-1\n- Severity: \"high\"\n## Issue A-2\n- Severity: \"medium\"\n"
    with pytest.raises(ValueError, match="require one handoff_item"):
        RUNTIME.detect_request_source(sealed("audit", body))
    assert RUNTIME.detect_request_source(sealed("audit", body), "A-2")["item"] == "A-2"
    with pytest.raises(ValueError, match="does not contain"):
        RUNTIME.detect_request_source(sealed("audit", body), "A-9")


def test_generic_requests_remain_supported() -> None:
    assert RUNTIME.detect_request_source(b"Please add the requested behavior.\n") == {"kind": "generic", "contract_version": None, "item": None}


@pytest.mark.parametrize(
    "handoff_bytes",
    [
        sealed("audit", "# Audit Issue Handoff\n## Issues\nNo accepted findings.\n"),
        sealed("optimization", "- H-1: next: needs-evidence | candidate: C-1\n"),
        sealed("issue", '<!-- issue-handoff-metadata -->\n```json\n{"status":"blocked"}\n```\n'),
    ],
)
def test_terminal_handoffs_are_rejected(handoff_bytes: bytes) -> None:
    with pytest.raises(ValueError):
        RUNTIME.detect_request_source(handoff_bytes)


def test_rejects_tampered_unknown_and_unsupported_handoffs() -> None:
    tampered = sealed("design", "body\n") + b"changed"
    with pytest.raises(ValueError, match="does not match"):
        RUNTIME.detect_request_source(tampered)
    with pytest.raises(ValueError, match="Unsupported"):
        RUNTIME.detect_request_source(sealed("design", "body\n", version=2))
    with pytest.raises(ValueError, match="unknown or unsupported"):
        RUNTIME.detect_request_source(b"<!-- mystery-handoff: 1; sha256: deadbeef -->\nbody")


def test_selector_is_rejected_for_non_audit_input() -> None:
    with pytest.raises(ValueError, match="only for audit"):
        RUNTIME.detect_request_source(sealed("design", "body\n"), "D-1")


def test_typed_handoff_plans_require_matching_rq_source_and_audit_anchor(tmp_path: Path) -> None:
    helpers_spec = importlib.util.spec_from_file_location(
        "plan_change_v7_helpers",
        ROOT / "tests" / "skills" / "plan-change" / "v7_helpers.py",
    )
    assert helpers_spec and helpers_spec.loader
    helpers = importlib.util.module_from_spec(helpers_spec)
    helpers_spec.loader.exec_module(helpers)

    repo = helpers.make_repo(tmp_path / "repo")
    body = "# Audit\n## Issue FND-2\nNormalize absent values safely.\n## Issue FND-9\nUnrelated finding.\n"
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_bytes(sealed("audit", body))
    good = (
        helpers.tiny_plan(request_anchor="Normalize absent values safely")
        .replace("source: request", "source: audit")
        .replace(
            "obligation: absent input names must normalize to an empty string",
            "obligation: remediate selected finding absent-value normalization",
        )
    )
    draft.write_text(good, encoding="utf-8")
    sealed_plan = RUNTIME.seal_plan(repo, request, draft, handoff_item="FND-2")
    assert "<!-- plan-validation: 7;" in sealed_plan.text

    wrong_source = good.replace("source: audit", "source: request")
    draft.write_text(wrong_source, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as wrong_source_error:
        RUNTIME.seal_plan(repo, request, draft, handoff_item="FND-2")
    assert any(item.code == "obligation.source" for item in _diagnostics(wrong_source_error.value))

    wrong_finding = good.replace("Normalize absent values safely", "Unrelated finding")
    draft.write_text(wrong_finding, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as wrong_finding_error:
        RUNTIME.seal_plan(repo, request, draft, handoff_item="FND-2")
    assert any(item.code == "obligation.anchor" for item in _diagnostics(wrong_finding_error.value))


def test_bug_fix_requires_fail_before_or_regression_verification(tmp_path: Path) -> None:
    helpers_spec = importlib.util.spec_from_file_location(
        "plan_change_v7_helpers_bugfix",
        ROOT / "tests" / "skills" / "plan-change" / "v7_helpers.py",
    )
    assert helpers_spec and helpers_spec.loader
    helpers = importlib.util.module_from_spec(helpers_spec)
    helpers_spec.loader.exec_module(helpers)

    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    weak = helpers.tiny_plan().replace(
        "then: the case fails before the fix and passes after the fix with absent input empty and present input stripped",
        "then: absent input is empty and present input is stripped",
    )
    draft.write_text(weak, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "verification.regression" for item in _diagnostics(error.value))


def _load_helpers(name: str):
    helpers_spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "tests" / "skills" / "plan-change" / "v7_helpers.py",
    )
    assert helpers_spec and helpers_spec.loader
    helpers = importlib.util.module_from_spec(helpers_spec)
    helpers_spec.loader.exec_module(helpers)
    return helpers


def test_bug_fix_regression_ignores_command_path(tmp_path: Path) -> None:
    helpers = _load_helpers("plan_change_v7_helpers_bugfix_command")
    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    weak = (
        helpers.tiny_plan()
        .replace(
            "then: the case fails before the fix and passes after the fix with absent input empty and present input stripped",
            "then: absent input is empty and present input is stripped",
        )
        .replace(
            "command: python -m pytest tests/test_names.py -q",
            "command: python -m pytest tests/regression/test_names.py -q",
        )
    )
    draft.write_text(weak, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "verification.regression" for item in _diagnostics(error.value))


def test_irreversible_rollout_requires_concrete_content(tmp_path: Path) -> None:
    helpers = _load_helpers("plan_change_v7_helpers_irreversible_rollout")
    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Deny unauthorized tenant names.\n", encoding="utf-8")
    weak = (
        helpers.high_risk_plan()
        .replace("reversibility: reversible", "reversibility: irreversible")
        .replace(
            "## Verification\n",
            "## Rollout and Rollback\n"
            "Ship the authorization change carefully after review.\n"
            "\n## Verification\n",
        )
    )
    draft.write_text(weak, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "rollout.invalid" for item in _diagnostics(error.value))


def test_dependency_missing_and_cycle_are_rejected(tmp_path: Path) -> None:
    helpers = _load_helpers("plan_change_v7_helpers_dependency")
    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text(helpers.DEFAULT_REQUEST, encoding="utf-8")

    missing = helpers.tiny_plan().replace("depends_on: none", "depends_on: CH-9")
    draft.write_text(missing, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as missing_error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "dependency.missing" for item in _diagnostics(missing_error.value))

    cyclic = helpers.tiny_plan().replace(
        "CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: return the empty string for absent values before stripping present names | "
        "depends_on: none | locality: local | reversibility: reversible",
        "CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: return the empty string for absent values before stripping present names | "
        "depends_on: CH-2 | locality: local | reversibility: reversible\n"
        "CH-2: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: keep stripping present names after absent values normalize | "
        "depends_on: CH-1 | locality: local | reversibility: reversible",
    ).replace(
        "T-1: covers: SC-1, CH-1 |",
        "T-1: covers: SC-1, CH-1, CH-2 |",
    ).replace(
        "covered_by: SC-1, CH-1, T-1",
        "covered_by: SC-1, CH-1, CH-2, T-1",
    )
    draft.write_text(cyclic, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as cycle_error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "dependency.cycle" for item in _diagnostics(cycle_error.value))


def test_dependency_order_is_recorded_in_proof(tmp_path: Path) -> None:
    helpers = _load_helpers("plan_change_v7_helpers_dependency_order")
    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text(helpers.DEFAULT_REQUEST, encoding="utf-8")
    ordered = helpers.tiny_plan().replace(
        "CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: return the empty string for absent values before stripping present names | "
        "depends_on: none | locality: local | reversibility: reversible",
        "CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: return the empty string for absent values before stripping present names | "
        "depends_on: none | locality: local | reversibility: reversible\n"
        "CH-2: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | "
        "change: document the empty-string contract beside the normalize_name owner | "
        "depends_on: CH-1 | locality: local | reversibility: reversible",
    ).replace(
        "T-1: covers: SC-1, CH-1 |",
        "T-1: covers: SC-1, CH-1, CH-2 |",
    ).replace(
        "covered_by: SC-1, CH-1, T-1",
        "covered_by: SC-1, CH-1, CH-2, T-1",
    )
    draft.write_text(ordered, encoding="utf-8")
    sealed = RUNTIME.seal_plan(repo, request, draft)
    assert sealed.proof["change_order"] == ["CH-1", "CH-2"]


def test_design_optimization_issue_anchors_must_use_selected_material(tmp_path: Path) -> None:
    helpers = _load_helpers("plan_change_v7_helpers_selected_material")
    repo = helpers.make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"

    design_body = (
        "## Chosen Design & Depth Rationale\n"
        "- Boundary: NameGateway.normalize owns absent-name handling\n"
        "## Alternatives Considered\n"
        "### Alternative: RejectedStripOnly\n"
        "- Boundary: strip-only helper without gateway\n"
    )
    request.write_bytes(sealed("design", design_body))
    good = (
        helpers.tiny_plan(request_anchor="NameGateway.normalize owns absent-name handling")
        .replace("source: request", "source: design")
        .replace(
            "obligation: absent input names must normalize to an empty string",
            "obligation: implement the selected NameGateway.normalize boundary",
        )
    )
    draft.write_text(good, encoding="utf-8")
    assert "<!-- plan-validation: 7;" in RUNTIME.seal_plan(repo, request, draft).text
    bad = good.replace("NameGateway.normalize owns absent-name handling", "strip-only helper without gateway")
    draft.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as design_error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "obligation.anchor" for item in _diagnostics(design_error.value))

    opt_body = (
        "- Selected candidate: C-1\n"
        "- H-1: next: plan-ready | candidate: C-1 | measure: p95 latency\n"
        "- C-1: cache normalize_name for repeated inputs\n"
        "- C-9: rejected speculative rewrite\n"
    )
    request.write_bytes(sealed("optimization", opt_body))
    good_opt = (
        helpers.tiny_plan(request_anchor="cache normalize_name for repeated inputs")
        .replace("source: request", "source: optimization")
        .replace(
            "obligation: absent input names must normalize to an empty string",
            "obligation: apply selected candidate cache measure for the workflow",
        )
        .replace('{"intent":"bug-fix","tier":"tiny","risk_domains":[]}', '{"intent":"feature","tier":"tiny","risk_domains":[]}')
        .replace(
            "then: the case fails before the fix and passes after the fix with absent input empty and present input stripped",
            "then: cached repeated inputs match the measured workflow expectation",
        )
    )
    draft.write_text(good_opt, encoding="utf-8")
    assert "<!-- plan-validation: 7;" in RUNTIME.seal_plan(repo, request, draft).text
    bad_opt = good_opt.replace("cache normalize_name for repeated inputs", "rejected speculative rewrite")
    draft.write_text(bad_opt, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as opt_error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "obligation.anchor" for item in _diagnostics(opt_error.value))

    issue_body = (
        "## Outcome and Scope\n"
        "Return empty string for absent names.\n"
        "## Constraints and Protected Behavior\n"
        "Protect current strip behavior for present names.\n"
        "## Risks and Open Questions\n"
        "Incidental prose must not be used as an obligation anchor.\n"
    )
    request.write_bytes(sealed("issue", '<!-- issue-handoff-metadata -->\n```json\n{"status":"plan-ready"}\n```\n' + issue_body))
    good_issue = (
        helpers.tiny_plan(request_anchor="Protect current strip behavior")
        .replace("source: request", "source: issue")
        .replace(
            "obligation: absent input names must normalize to an empty string",
            "obligation: fix absent names while protecting strip behavior",
        )
    )
    draft.write_text(good_issue, encoding="utf-8")
    assert "<!-- plan-validation: 7;" in RUNTIME.seal_plan(repo, request, draft).text
    bad_issue = good_issue.replace("Protect current strip behavior", "Incidental prose must not be used")
    draft.write_text(bad_issue, encoding="utf-8")
    with pytest.raises(ValueError, match="draft validation failed") as issue_error:
        RUNTIME.seal_plan(repo, request, draft)
    assert any(item.code == "obligation.anchor" for item in _diagnostics(issue_error.value))
