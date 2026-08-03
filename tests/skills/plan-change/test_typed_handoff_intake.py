from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

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
