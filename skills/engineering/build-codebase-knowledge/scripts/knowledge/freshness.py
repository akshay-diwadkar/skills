"""Freshness checking and true semantic incremental refresh engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from knowledge.config import load_config
from knowledge.discovery import is_secret_file_or_content
from knowledge.extraction.javascript import extract_javascript_file
from knowledge.extraction.lexical import extract_lexical_file
from knowledge.extraction.python import extract_python_file
from knowledge.fingerprint import compute_file_hash, compute_source_fingerprint
from knowledge.relationships import build_relationship_graph
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic
from knowledge.summaries import format_architecture_md, format_context_md


def check_freshness(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    """Check repository knowledge freshness using source fingerprinting and file hashes."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    k_dir = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]

    manifest_path = k_dir / "manifest.json"
    index_path = k_dir / "index.json"

    if not manifest_path.is_file() or not index_path.is_file():
        return {"status": "missing", "reason": "Knowledge artifacts missing."}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "invalid", "reason": f"Artifacts unreadable: {exc}"}

    # Validate JSON schemas
    m_errors = validate_schema_json(manifest, "manifest.schema.json")
    i_errors = validate_schema_json(index, "index.schema.json")
    if m_errors or i_errors:
        return {"status": "invalid", "reason": f"Schema validation failed: {m_errors + i_errors}"}

    indexed_paths = manifest.get("indexed_paths", [])
    current_fp = compute_source_fingerprint(root, indexed_paths, config)
    stored_fp = manifest.get("source_fingerprint", "")

    file_hashes = manifest.get("file_hashes", {})
    changed: list[str] = []

    for rel_path, old_hash in file_hashes.items():
        full_p = root / rel_path
        if not full_p.is_file():
            changed.append(rel_path)
        else:
            new_hash = compute_file_hash(full_p)
            if new_hash != old_hash:
                changed.append(rel_path)

    if changed:
        return {
            "status": "partially-stale",
            "changed_files": sorted(changed),
            "reason": f"{len(changed)} file(s) modified or deleted.",
        }

    if stored_fp and current_fp != stored_fp:
        return {"status": "stale", "reason": "Source fingerprint mismatch."}

    return {"status": "fresh", "changed_files": []}


def refresh_knowledge(
    repo_root: Path | str,
    changed_files: list[str] | None = None,
    knowledge_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Perform true semantic incremental refresh or fall back to full rebuild if change ratio > threshold."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    k_dir = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]

    # Import build_knowledge locally to avoid circular dependency
    from build_knowledge import build_knowledge

    freshness = check_freshness(root, k_dir)
    if freshness["status"] in ["missing", "invalid", "stale"]:
        res = build_knowledge(root, k_dir)
        return {"mode": "full", "status": "fresh", "details": res}

    files_to_update = sorted(list(set(changed_files))) if changed_files else freshness.get("changed_files", [])
    if not files_to_update:
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh."}

    manifest_path = k_dir / "manifest.json"
    index_path = k_dir / "index.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))

    total_indexed = len(manifest.get("indexed_paths", []))
    ratio = len(files_to_update) / max(total_indexed, 1)
    threshold = config.get("full_refresh_change_ratio", 0.20)

    if ratio > threshold and total_indexed > 5:
        res = build_knowledge(root, k_dir)
        return {
            "mode": "full",
            "status": "fresh",
            "reason": f"Change ratio ({ratio:.2f}) exceeded threshold ({threshold:.2f})",
            "details": res,
        }

    # True semantic incremental re-extraction
    file_map = {f["path"]: f for f in index.get("files", [])}
    symbols_list = [s for s in index.get("symbols", []) if s["path"] not in files_to_update]
    file_hashes = manifest.get("file_hashes", {})

    for rel_str in files_to_update:
        full_p = root / rel_str
        if not full_p.is_file():
            # File deleted: remove from index & manifest
            file_map.pop(rel_str, None)
            file_hashes.pop(rel_str, None)
            if rel_str in manifest["indexed_paths"]:
                manifest["indexed_paths"].remove(rel_str)
            continue

        # File modified/added: re-extract semantically
        try:
            content = full_p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if is_secret_file_or_content(full_p, content):
            file_map.pop(rel_str, None)
            file_hashes.pop(rel_str, None)
            continue

        file_hash = compute_file_hash(full_p)
        file_hashes[rel_str] = file_hash
        if rel_str not in manifest["indexed_paths"]:
            manifest["indexed_paths"].append(rel_str)

        suffix = full_p.suffix.lower()
        subsystem = rel_str.split("/")[0] if "/" in rel_str else "root"
        role = "test" if ("test" in rel_str.lower() or full_p.name.startswith("test_")) else "source"

        extracted_symbols: list[dict[str, Any]] = []
        raw_imports: list[str] = []

        if suffix == ".py":
            ext_syms, raw_imports, _, _ = extract_python_file(full_p, rel_str, content, subsystem)
            for s in ext_syms:
                extracted_symbols.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                    "docstring": s.docstring,
                })
        elif suffix in [".js", ".ts", ".jsx", ".tsx"]:
            ext_syms, raw_imports, _, _ = extract_javascript_file(full_p, rel_str, content, subsystem)
            for s in ext_syms:
                extracted_symbols.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                })
        elif suffix in [".go", ".rs", ".java", ".c", ".cpp"]:
            ext_syms, raw_imports, _, _ = extract_lexical_file(full_p, rel_str, content, subsystem)
            for s in ext_syms:
                extracted_symbols.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                })

        symbols_list.extend(extracted_symbols)

        file_map[rel_str] = {
            "path": rel_str,
            "subsystem": subsystem,
            "role": role,
            "symbols": [s["name"] for s in extracted_symbols],
            "imports": raw_imports,
            "imported_by": [],
            "tests": [],
            "keywords": sorted(list(set([subsystem, role, Path(rel_str).stem] + [s["name"] for s in extracted_symbols[:5]]))),
            "hash": file_hash,
            "role_summary": f"{role.capitalize()} module in {subsystem} subsystem.",
        }

    # Rebuild relationships across updated file set
    updated_files_list = sorted(list(file_map.values()), key=lambda f: f["path"])
    updated_files, updated_deps, updated_tests = build_relationship_graph(
        updated_files_list, index.get("tests", [])
    )

    import hashlib
    manifest["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
    manifest["indexed_paths"] = sorted(manifest["indexed_paths"])
    manifest["file_hashes"] = file_hashes
    manifest["source_fingerprint"] = compute_source_fingerprint(root, manifest["indexed_paths"], config)
    manifest["changed_files"] = files_to_update
    manifest["freshness_state"] = "fresh"

    index["files"] = updated_files
    index["symbols"] = sorted(symbols_list, key=lambda s: (s["path"], s["line_start"], s["name"]))
    index["dependencies"] = updated_deps
    index["tests"] = updated_tests

    # Validate before saving
    sem_errors = validate_semantic_graph(root, index, manifest)
    if sem_errors:
        return {"mode": "error", "status": "invalid", "errors": sem_errors}

    write_file_deterministic(manifest_path, serialize_json_deterministic(manifest))
    write_file_deterministic(index_path, serialize_json_deterministic(index))

    # Regenerate summaries
    rev = manifest.get("repository", {}).get("revision", "unknown")
    subsystems_map: dict[str, list[str]] = {}
    for f in updated_files:
        sub = f["subsystem"]
        if sub not in subsystems_map:
            subsystems_map[sub] = []
        subsystems_map[sub].append(f["path"])

    context_md = format_context_md(
        revision=rev,
        subsystems=subsystems_map,
        languages=index.get("repository", {}).get("languages", []),
        entry_points=index.get("entry_points", []),
        commands=[],
    )
    arch_md = format_architecture_md(
        revision=rev,
        subsystems=subsystems_map,
        dependencies=updated_deps,
        tests=updated_tests,
        configurations=index.get("configurations", []),
    )

    write_file_deterministic(k_dir / "context.md", context_md)
    write_file_deterministic(k_dir / "architecture.md", arch_md)

    return {
        "mode": "incremental",
        "status": "fresh",
        "updated_files": len(files_to_update),
    }
