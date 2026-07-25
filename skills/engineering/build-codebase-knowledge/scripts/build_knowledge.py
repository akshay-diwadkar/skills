#!/usr/bin/env python3
"""Build codebase knowledge artifacts: context.md, architecture.md, index.json, manifest.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge.config import load_config
from knowledge.discovery import discover_files, is_secret_file_or_content
from knowledge.extraction.configuration import extract_config_and_commands
from knowledge.extraction.javascript import extract_javascript_file
from knowledge.extraction.lexical import extract_lexical_file
from knowledge.extraction.python import extract_python_file
from knowledge.fingerprint import compute_file_hash, compute_source_fingerprint
from knowledge.relationships import build_relationship_graph
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic
from knowledge.summaries import format_architecture_md, format_context_md
from link_agent_docs import link_agent_docs


def get_git_info(repo_root: Path) -> tuple[str, str, bool]:
    """Extract git commit revision, branch, and dirty status safely."""
    import subprocess
    revision = "unknown"
    branch = "unknown"
    dirty = False

    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return revision, branch, dirty

    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False)
        if rev.returncode == 0:
            revision = rev.stdout.strip()

        br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False)
        if br.returncode == 0:
            branch = br.stdout.strip()

        st = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=False)
        if st.returncode == 0 and st.stdout.strip():
            dirty = True
    except Exception:
        pass
    return revision, branch, dirty


def build_knowledge(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Build complete codebase knowledge artifacts for target repository."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    out_dir = Path(output_dir).resolve() if output_dir else root / config["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    included_files, generated_files, ignored_files = discover_files(root, config)

    files_list: list[dict[str, Any]] = []
    symbols_list: list[dict[str, Any]] = []
    entry_points: list[dict[str, Any]] = []
    configurations: list[dict[str, Any]] = []
    detected_commands: list[dict[str, str]] = []
    tests_list: list[dict[str, Any]] = []
    subsystems_map: dict[str, list[str]] = {}
    languages_set: set[str] = set()
    file_hashes: dict[str, str] = {}
    unknowns_list: list[str] = []

    for rel_str in included_files:
        full_path = root / rel_str
        file_hash = compute_file_hash(full_path)
        file_hashes[rel_str] = file_hash

        suffix = full_path.suffix.lower()
        content = ""
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            unknowns_list.append(f"Could not read content of {rel_str}: {exc}")
            continue

        if is_secret_file_or_content(full_path, content):
            ignored_files.append(rel_str)
            file_hashes.pop(rel_str, None)
            continue

        # Language detection
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
        }
        lang = lang_map.get(suffix, "")
        if lang:
            languages_set.add(lang)

        # Subsystem assignment
        subsystem = rel_str.split("/")[0] if "/" in rel_str else "root"
        if subsystem not in subsystems_map:
            subsystems_map[subsystem] = []
        subsystems_map[subsystem].append(rel_str)

        # Config & command extraction
        if suffix in [".toml", ".yaml", ".yml", ".json", ".ini"] or rel_str.endswith(".env.example"):
            cfg_entry, cmds = extract_config_and_commands(root, rel_str, content)
            configurations.append(cfg_entry)
            detected_commands.extend(cmds)

        # Role & symbol extraction
        role = "source"
        if "test" in rel_str.lower() or (suffix == ".py" and full_path.name.startswith("test_")):
            role = "test"
            target_stem = rel_str.replace("tests/", "src/").replace("test_", "").replace("_test", "")
            tests_list.append({"path": rel_str, "targets": [target_stem]})

        file_symbols: list[str] = []
        file_imports: list[str] = []

        if suffix == ".py":
            ext_syms, raw_imports, _, unks = extract_python_file(full_path, rel_str, content, subsystem)
            unknowns_list.extend(unks)
            for s in ext_syms:
                symbols_list.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                    "docstring": s.docstring,
                })
                file_symbols.append(s.name)
            file_imports = raw_imports

        elif suffix in [".js", ".ts", ".jsx", ".tsx"]:
            ext_syms, raw_imports, _, unks = extract_javascript_file(full_path, rel_str, content, subsystem)
            unknowns_list.extend(unks)
            for s in ext_syms:
                symbols_list.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                })
                file_symbols.append(s.name)
            file_imports = raw_imports

        elif suffix in [".go", ".rs", ".java", ".c", ".cpp"]:
            ext_syms, raw_imports, _, unks = extract_lexical_file(full_path, rel_str, content, subsystem)
            unknowns_list.extend(unks)
            for s in ext_syms:
                symbols_list.append({
                    "name": s.name,
                    "qualified_name": s.qualified_name,
                    "kind": s.kind,
                    "path": s.path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "subsystem": s.subsystem,
                })
                file_symbols.append(s.name)
            file_imports = raw_imports

        # Entry point detection
        lower_path = rel_str.lower()
        if any(ep in lower_path for ep in ["main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py", "main.go", "main.rs"]) or "if __name__ == '__main__':" in content or "def main(" in content:
            entry_points.append({
                "name": rel_str,
                "path": rel_str,
                "symbol": file_symbols[0] if file_symbols else "main",
                "kind": "entry-point",
            })

        keywords = sorted(list(set([subsystem, role, Path(rel_str).stem] + file_symbols[:5])))

        files_list.append({
            "path": rel_str,
            "subsystem": subsystem,
            "role": role,
            "symbols": file_symbols,
            "imports": file_imports,
            "imported_by": [],
            "tests": [],
            "keywords": keywords,
            "hash": file_hash,
            "role_summary": f"{role.capitalize()} module in {subsystem} subsystem.",
        })

    # Sort inputs deterministically
    files_list = sorted(files_list, key=lambda f: f["path"])
    symbols_list = sorted(symbols_list, key=lambda s: (s["path"], s["line_start"], s["name"]))
    entry_points = sorted(entry_points, key=lambda ep: ep["path"])
    configurations = sorted(configurations, key=lambda c: c["path"])

    # Build bidirectional graph
    files_list, dependencies_list, tests_list = build_relationship_graph(files_list, tests_list)

    revision, branch, dirty = get_git_info(root)
    source_fp = compute_source_fingerprint(root, [f["path"] for f in files_list], config)

    index_data = {
        "schema_version": "1.0",
        "repository": {
            "root": ".",
            "revision": revision,
            "languages": sorted(list(languages_set)),
            "frameworks": [],
        },
        "subsystems": [
            {"name": k, "paths": sorted(v), "description": f"{k.capitalize()} subsystem."}
            for k, v in sorted(subsystems_map.items())
        ],
        "files": files_list,
        "symbols": symbols_list,
        "entry_points": entry_points,
        "flows": [
            {"name": "Main Execution Flow", "kind": "entry", "steps": [ep["path"] for ep in entry_points]}
        ],
        "dependencies": dependencies_list,
        "tests": tests_list,
        "configurations": configurations,
        "generated_paths": sorted(generated_files),
        "ignored_paths": sorted(ignored_files),
    }

    manifest_data = {
        "schema_version": "1.0",
        "generator_version": "2.0.0",
        "repository": {
            "root": ".",
            "revision": revision,
            "branch": branch,
            "dirty": dirty,
        },
        "generation_mode": "full",
        "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16],
        "source_fingerprint": source_fp,
        "indexed_paths": [f["path"] for f in files_list],
        "ignored_paths": sorted(ignored_files),
        "changed_files": [],
        "file_hashes": file_hashes,
        "freshness_state": "fresh",
    }

    # Validate JSON schemas and graph consistency
    m_errors = validate_schema_json(manifest_data, "manifest.schema.json")
    i_errors = validate_schema_json(index_data, "index.schema.json")
    sem_errors = validate_semantic_graph(root, index_data, manifest_data)

    all_errors = m_errors + i_errors + sem_errors
    if all_errors:
        raise ValueError(f"Knowledge build validation failed: {all_errors}")

    # Write files deterministically
    write_file_deterministic(out_dir / "index.json", serialize_json_deterministic(index_data))
    write_file_deterministic(out_dir / "manifest.json", serialize_json_deterministic(manifest_data))

    context_md = format_context_md(
        revision=revision,
        subsystems=subsystems_map,
        languages=sorted(list(languages_set)),
        entry_points=entry_points,
        commands=detected_commands,
        unknowns=unknowns_list,
    )
    arch_md = format_architecture_md(
        revision=revision,
        subsystems=subsystems_map,
        dependencies=dependencies_list,
        tests=tests_list,
        configurations=configurations,
    )

    write_file_deterministic(out_dir / "context.md", context_md)
    write_file_deterministic(out_dir / "architecture.md", arch_md)

    # Link AGENTS.md / CLAUDE.md managed blocks
    link_agent_docs(root, out_dir)

    return {
        "status": "success",
        "output_dir": str(out_dir),
        "files_indexed": len(files_list),
        "symbols_indexed": len(symbols_list),
        "source_fingerprint": source_fp,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build codebase knowledge artifacts.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Output directory for knowledge artifacts")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.output).resolve() if args.output else None

    res = build_knowledge(repo_root, out_dir)
    if not args.quiet:
        print(f"Build completed: {res['files_indexed']} files, {res['symbols_indexed']} symbols indexed -> {res['output_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
