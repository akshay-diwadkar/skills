from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from finalize_manual import finalize


def test_finalizer_stamps_canonical_receipt_and_is_idempotent(
    manual_case: tuple[Path, Path, Path, dict[str, Any]],
) -> None:
    repo, manual, bundle_path, _bundle = manual_case
    status, output = finalize(repo, bundle_path, manual)
    assert status == 0
    assert output == {
        "status": "final",
        "manual_hash": "sha256:" + hashlib.sha256(manual.read_bytes()).hexdigest(),
        "language_pass": True,
        "semantic_pass": True,
        "receipt": "validated",
    }
    first = bundle_path.read_bytes()
    finalized = json.loads(first)
    receipt = finalized.pop("validation_receipt")
    expected = hashlib.sha256(
        json.dumps(finalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert receipt["bundle_hash"] == f"sha256:{expected}"
    assert receipt["manual_hash"] == output["manual_hash"]

    status, _ = finalize(repo, bundle_path, manual)
    assert status == 0
    assert bundle_path.read_bytes() == first


def test_failed_finalization_does_not_mutate_inputs(
    manual_case: tuple[Path, Path, Path, dict[str, Any]],
) -> None:
    repo, manual, bundle_path, _bundle = manual_case
    manual.write_text("Install the package and restart the service.\n", encoding="utf-8")
    before = (manual.read_bytes(), bundle_path.read_bytes())
    status, output = finalize(repo, bundle_path, manual)
    assert status == 1
    assert output["language_pass"] is False
    assert (manual.read_bytes(), bundle_path.read_bytes()) == before


def test_audit_bundle_cannot_receive_receipt(
    manual_case: tuple[Path, Path, Path, dict[str, Any]],
) -> None:
    repo, manual, bundle_path, bundle = manual_case
    bundle["operation"] = "audit"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    before = bundle_path.read_bytes()
    status, output = finalize(repo, bundle_path, manual)
    assert status == 1
    assert output["status"] == "invalid"
    assert bundle_path.read_bytes() == before
