#!/usr/bin/env python3
"""Incremental refresh and cheap freshness validation engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from build_knowledge import build_knowledge, compute_file_hash, get_git_info, load_config

def check_freshness(repo_root: Path, knowledge_dir: Path | None = None) -> dict[str, Any]:
    k_dir = knowledge_dir if knowledge_dir else repo_root / ".agent" / "knowledge"
    manifest_path = k_dir / "manifest.json"
    index_path = k_dir / "index.json"

    if not manifest_path.is_file() or not index_path.is_file():
        return {"status": "missing", "reason": "Artifacts missing"}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "invalid", "reason": f"Manifest unreadable: {e}"}

    rev, branch, dirty = get_git_info(repo_root)
    stored_rev = manifest.get("repository", {}).get("revision", "")

    if rev != "unknown" and stored_rev and rev != stored_rev:
        return {"status": "stale", "reason": f"Revision mismatch ({rev} != {stored_rev})"}

    file_hashes = manifest.get("file_hashes", {})
    changed = []
    for rel_path, old_hash in file_hashes.items():
        full_p = repo_root / rel_path
        if not full_p.is_file():
            changed.append(rel_path)
        else:
            new_hash = compute_file_hash(full_p)
            if new_hash != old_hash:
                changed.append(rel_path)

    if changed:
        return {"status": "partially-stale", "changed_files": changed, "reason": f"{len(changed)} files modified"}

    return {"status": "fresh", "changed_files": []}

def refresh_knowledge(repo_root: Path, changed_files: list[str] | None = None, knowledge_dir: Path | None = None) -> dict[str, Any]:
    k_dir = knowledge_dir if knowledge_dir else repo_root / ".agent" / "knowledge"
    config = load_config(repo_root)

    status_info = check_freshness(repo_root, k_dir)
    if status_info["status"] in ["missing", "invalid", "stale"]:
        # Trigger full rebuild
        res = build_knowledge(repo_root, k_dir)
        return {"mode": "full", "status": "fresh", "details": res}

    files_to_update = list(changed_files) if changed_files else status_info.get("changed_files", [])
    if not files_to_update:
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh."}

    manifest_path = k_dir / "manifest.json"
    index_path = k_dir / "index.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))

    total_indexed = len(manifest.get("indexed_paths", []))
    ratio = len(files_to_update) / max(total_indexed, 1)

    threshold = config.get("full_refresh_change_ratio", 0.20)
    if ratio > threshold:
        res = build_knowledge(repo_root, k_dir)
        return {"mode": "full", "status": "fresh", "reason": f"Change ratio ({ratio:.2f}) exceeded threshold ({threshold:.2f})", "details": res}

    # Incremental update: update file hashes and revision
    rev, branch, dirty = get_git_info(repo_root)
    file_hashes = manifest.get("file_hashes", {})

    for rel_str in files_to_update:
        full_p = repo_root / rel_str
        if full_p.is_file():
            file_hashes[rel_str] = compute_file_hash(full_p)
            if rel_str not in manifest["indexed_paths"]:
                manifest["indexed_paths"].append(rel_str)
        else:
            file_hashes.pop(rel_str, None)
            if rel_str in manifest["indexed_paths"]:
                manifest["indexed_paths"].remove(rel_str)
            index["files"] = [f for f in index.get("files", []) if f["path"] != rel_str]
            index["symbols"] = [s for s in index.get("symbols", []) if s["path"] != rel_str]

    manifest["repository"]["revision"] = rev
    manifest["repository"]["branch"] = branch
    manifest["repository"]["dirty"] = dirty
    manifest["file_hashes"] = file_hashes
    manifest["changed_files"] = files_to_update
    manifest["freshness_state"] = "fresh"

    index["repository"]["revision"] = rev

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    return {
        "mode": "incremental",
        "status": "fresh",
        "updated_files": len(files_to_update)
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh codebase knowledge incrementally.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--changed-file", action="append", default=[], help="Explicitly changed file path")
    parser.add_argument("--output", help="Output directory")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    k_dir = Path(args.output).resolve() if args.output else None

    res = refresh_knowledge(repo_root, args.changed_file, k_dir)
    print(f"Refresh completed ({res['mode']} mode): status={res['status']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
