#!/usr/bin/env python3
"""Tests for the versioned audit bundle contract."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[1]
RUNTIME_SCRIPTS = REPO_ROOT / "codebase-issue-auditor" / "scripts"
for import_path in (RUNTIME_SCRIPTS, DEV_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import audit_bundle  # noqa: E402
import score_audit_evaluation  # noqa: E402
import validate_audit_bundle  # noqa: E402


FIXTURE_DIR = DEV_DIR / "fixtures"
VALID_BUNDLE_PATH = FIXTURE_DIR / "valid_bundle.json"
LEGACY_ISSUES_PATH = FIXTURE_DIR / "legacy_issues.json"


def valid_bundle() -> dict[str, Any]:
    raw = json.loads(VALID_BUNDLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


class AuditBundleTests(unittest.TestCase):
    def assert_error_contains(self, bundle: dict[str, Any], expected: str) -> None:
        errors = audit_bundle.validate_audit_bundle(bundle)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_valid_bundle_passes(self):
        self.assertEqual(audit_bundle.validate_audit_bundle(valid_bundle()), [])

    def test_incomplete_coverage_is_rejected(self):
        bundle = valid_bundle()
        bundle["coverage"] = []
        self.assert_error_contains(bundle, "coverage is missing subsystem/category pair")

    def test_unsupported_evidence_is_rejected(self):
        bundle = valid_bundle()
        candidate = bundle["candidates"][0]
        candidate["evidence"] = [
            {"kind": "external", "location": "https://example.test", "observation": "Generic advice"}
        ]
        self.assert_error_contains(bundle, "at least two observations")
        self.assert_error_contains(bundle, "must contain local evidence")

    def test_missing_verification_is_rejected(self):
        bundle = valid_bundle()
        bundle["candidates"][0]["verification"] = []
        self.assert_error_contains(bundle, ".verification must be a non-empty array")

    def test_invalid_category_severity_confidence_and_decision_are_rejected(self):
        cases = {
            "category": "other",
            "severity": "urgent",
            "confidence": "certain",
            "decision": "pending",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                bundle = valid_bundle()
                bundle["candidates"][0][field] = value
                self.assert_error_contains(bundle, f".{field} must be one of")

    def test_accepted_candidate_requires_exactly_one_issue(self):
        bundle = valid_bundle()
        bundle["issues"] = []
        self.assert_error_contains(bundle, "issues are missing accepted candidate(s): C-001")

    def test_duplicate_root_causes_are_rejected(self):
        bundle = valid_bundle()
        duplicate = copy.deepcopy(bundle["candidates"][0])
        duplicate["id"] = "C-002"
        duplicate["title"] = "Duplicate candidate"
        bundle["candidates"].append(duplicate)
        bundle["issues"].append(
            {"candidate_id": "C-002", "title": "Duplicate candidate", "labels": ["audit", "bug"]}
        )
        self.assert_error_contains(bundle, "root_cause duplicates accepted candidate")

    def test_high_risk_deferment_requires_reported_limitation(self):
        bundle = valid_bundle()
        candidate = bundle["candidates"][0]
        candidate["decision"] = "deferred"
        bundle["issues"] = []
        bundle["rejects"] = [
            {
                "id": "R-001",
                "candidate_id": "C-001",
                "reason": "Production dependency unavailable",
                "evidence": ["The required service cannot be started locally."],
            }
        ]
        surface = bundle["risk_surfaces"][0]
        surface["status"] = "deferred"
        surface["candidate_ids"] = []
        surface["reject_ids"] = ["R-001"]
        self.assert_error_contains(bundle, "audit_context.limitations must explain it")

        bundle["audit_context"]["limitations"] = ["Production dependency unavailable"]
        self.assertEqual(audit_bundle.validate_audit_bundle(bundle), [])

    def test_legacy_input_remains_supported(self):
        drafts = audit_bundle.issues_from_input(audit_bundle.read_json(LEGACY_ISSUES_PATH))
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].title, "Preserve an explicit zero retry count")
        self.assertEqual(drafts[0].candidate_id, "")

    def test_structured_body_is_deterministic(self):
        draft = audit_bundle.issues_from_input(valid_bundle())[0]
        first = audit_bundle.format_issue_body(draft)
        second = audit_bundle.format_issue_body(draft)
        self.assertEqual(first, second)
        self.assertIn("## Verification", first)
        self.assertIn("Candidate: `C-001`", first)
        self.assertIn("Confidence: `high`", first)

    def test_evaluation_scorer_checks_recall_and_decoys(self):
        expectations = {
            "expected_findings": [{"id": "zero-retry", "keywords": ["zero", "retr"]}],
            "forbidden_findings": [{"id": "file-leak", "keywords": ["load_text", "leak"]}],
        }
        self.assertEqual(score_audit_evaluation.score(valid_bundle(), expectations), [])

        expectations["expected_findings"].append(
            {"id": "missing-finding", "keywords": ["authorization", "delete"]}
        )
        self.assertIn(
            "missing expected finding missing-finding",
            score_audit_evaluation.score(valid_bundle(), expectations),
        )

    def test_validator_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_path = Path(temp_dir) / "valid.json"
            invalid_path = Path(temp_dir) / "invalid.json"
            valid_path.write_text(json.dumps(valid_bundle()), encoding="utf-8")
            invalid = valid_bundle()
            invalid["coverage"] = []
            invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(validate_audit_bundle.main([str(valid_path)]), 0)
            self.assertIn("Audit bundle is valid", stdout.getvalue())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(validate_audit_bundle.main([str(invalid_path)]), 2)
            self.assertIn("coverage is missing", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
