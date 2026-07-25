#!/usr/bin/env python3
"""Validate codebase knowledge artifacts, schemas, paths, conciseness, and secret safety."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from build_knowledge import load_config
from refresh_knowledge import check_freshness

def validate_knowledge(repo_root: Path, knowledge_dir: Path | None = None) -> dict[str, Any]:
    k_dir = knowledge_dir if knowledge_dir else repo_root / ".agent" / "knowledge"
    config = load_config(repo_root)

    errors = []
    warnings = []

    index_path = k_dir / "index.json"
    manifest_path = k_dir / "manifest.json"
    context_path = k_dir / "context.md"
    arch_path = k_dir / "architecture.md"

    # Check existence
    for p in [index_path, manifest_path, context_path, arch_path]:
        if not p.is_file():
            errors.append(f"Missing required artifact: {p.name}")

    if errors:
        return {"status": "invalid", "errors": errors, "warnings": warnings}

    # Load JSON
    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "invalid", "errors": [f"JSON syntax error: {e}"], "warnings": warnings}

    # Verify paths exist on disk
    indexed_files = [f["path"] for f in index_data.get("files", [])]
    for rel_str in indexed_files:
        full_p = repo_root / rel_str
        if not full_p.is_file():
            errors.append(f"Indexed path does not exist on disk: {rel_str}")

    # Check conciseness & line limits
    max_context = config.get("max_context_lines", 120)
    max_arch = config.get("max_architecture_lines", 220)

    context_lines = context_path.read_text(encoding="utf-8").splitlines()
    if len(context_lines) > max_context:
        warnings.append(f"context.md line count ({len(context_lines)}) exceeds target ({max_context})")

    arch_lines = arch_path.read_text(encoding="utf-8").splitlines()
    if len(arch_lines) > max_arch:
        warnings.append(f"architecture.md line count ({len(arch_lines)}) exceeds target ({max_arch})")

    # Check secret leakage
    for p in [context_path, arch_path, index_path]:
        content = p.read_text(encoding="utf-8")
        if "BEGIN PRIVATE KEY" in content or "AWS_SECRET_ACCESS_KEY" in content:
            errors.append(f"Possible secret detected in artifact: {p.name}")

    # Check freshness status
    fresh_res = check_freshness(repo_root, k_dir)
    fresh_status = fresh_res.get("status", "fresh")

    if errors:
        final_status = "invalid"
    elif fresh_status == "partially-stale":
        final_status = "valid-partially-stale"
    elif fresh_status == "stale":
        final_status = "valid-stale"
    else:
        final_status = "valid-fresh"

    return {
        "status": final_status,
        "freshness": fresh_status,
        "errors": errors,
        "warnings": warnings,
        "files_checked": len(indexed_files),
        "context_lines": len(context_lines),
        "architecture_lines": len(arch_lines),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate codebase knowledge status.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Output knowledge directory")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    k_dir = Path(args.output).resolve() if args.output else None

    res = validate_knowledge(repo_root, k_dir)
    print(f"Validation status: {res['status']}")
    if res["warnings"]:
        for w in res["warnings"]:
            print(f"  Warning: {w}")
    if res["errors"]:
        for e in res["errors"]:
            print(f"  Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
