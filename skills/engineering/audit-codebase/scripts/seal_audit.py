#!/usr/bin/env python3
"""Validate one agent-owned audit bundle and append a local receipt."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from audit_bundle import read_json, validate_audit_bundle
from audit_handoff import render


def _verify_local_evidence(bundle: dict[str, Any], repo_root: Path) -> list[str]:
    """Verify only source/config/test evidence explicitly declared by the bundle."""
    errors: list[str] = []
    candidates = bundle.get("candidates", [])
    if not isinstance(candidates, list):
        return errors
    for candidate_index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        evidence_rows = candidate.get("evidence", [])
        if not isinstance(evidence_rows, list):
            continue
        for evidence_index, evidence in enumerate(evidence_rows):
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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    bundle = read_json(args.bundle)
    errors = validate_audit_bundle(bundle)
    if isinstance(bundle, dict):
        errors.extend(_verify_local_evidence(bundle, args.repo_root.resolve()))
    if errors:
        print("\n".join(errors))
        return 1
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be absolute")
    destination = args.output_dir / "audit-handoff.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=destination.parent, delete=False) as temp:
        temp.write(render(bundle))
        name = temp.name
    os.replace(name, destination)
    print(json.dumps({"status":"sealed", "path":str(destination), "issue_count":sum(c.get("decision") == "accepted" for c in bundle["candidates"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
