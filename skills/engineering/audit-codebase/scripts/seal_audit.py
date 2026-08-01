#!/usr/bin/env python3
"""Validate one agent-owned audit bundle and append a local receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from audit_bundle import read_json, validate_audit_bundle


def _verify_local_evidence(bundle: dict[object, object], repo_root: Path) -> list[str]:
    """Verify only source/config/test evidence explicitly declared by the bundle."""
    errors: list[str] = []
    for candidate_index, candidate in enumerate(bundle.get("candidates", [])):
        if not isinstance(candidate, dict):
            continue
        for evidence_index, evidence in enumerate(candidate.get("evidence", [])):
            if not isinstance(evidence, dict) or evidence.get("kind") not in {"source", "config", "test"}:
                continue
            location = evidence.get("location")
            if not isinstance(location, str):
                continue
            raw_path, separator, raw_line = location.rpartition(":")
            path_text = raw_path if separator and raw_line.isdecimal() else location
            path = (repo_root / path_text).resolve()
            label = f"candidates[{candidate_index}].evidence[{evidence_index}]"
            try:
                path.relative_to(repo_root)
            except ValueError:
                errors.append(f"{label} path escapes repository: {path_text}")
                continue
            if not path.is_file():
                errors.append(f"{label} path does not exist: {path_text}")
                continue
            if separator and raw_line.isdecimal():
                line_number = int(raw_line)
                if line_number < 1 or line_number > len(path.read_text(encoding="utf-8").splitlines()):
                    errors.append(f"{label} line is outside {path_text}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = read_json(args.bundle)
    errors = validate_audit_bundle(bundle)
    if isinstance(bundle, dict):
        errors.extend(_verify_local_evidence(bundle, args.repo_root.resolve()))
    if errors:
        print("\n".join(errors))
        return 1
    body = dict(bundle)
    body.pop("validation_receipt", None)
    bundle["validation_receipt"] = {"scope": "declared-bundle-only", "sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print('{"status":"sealed"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
