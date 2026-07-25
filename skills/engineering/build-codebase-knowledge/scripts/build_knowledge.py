#!/usr/bin/env python3
"""Build deterministic, sharded repository knowledge artifacts (v2)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge.config import load_config
from knowledge.discovery import discover_files, is_secret_file_or_content
from knowledge.extraction.configuration import extract_config_and_commands
from knowledge.extraction.javascript import extract_javascript_file
from knowledge.extraction.lexical import extract_lexical_file
from knowledge.extraction.python import extract_python_file
from knowledge.fingerprint import compute_file_hash
from knowledge.relationships import resolve_import_to_path
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic
from knowledge.summaries import format_architecture_md, format_context_md
from link_agent_docs import link_agent_docs
from scaffold_github_workflow import ensure_github_workflow

SCHEMA_VERSION = "2.0"
EXTRACTOR_VERSION = "3.0.0"
CONFIG_NAMES = {"pyproject.toml", "package.json", "makefile", "gnumakefile"}
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get_git_info(root: Path) -> tuple[str, str, bool, list[str]]:
    """Return the source snapshot that the knowledge artifacts describe."""

    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    return (
        git("rev-parse", "--short", "HEAD") or "unknown",
        git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        bool(git("status", "--porcelain")),
        sorted(line[3:] for line in git("ls-files", "--others", "--exclude-standard").splitlines() if line),
    )


def _role(path: str) -> str:
    name = Path(path).name.lower()
    if (
        name in CONFIG_NAMES
        or Path(path).suffix.lower() in {".toml", ".yaml", ".yml", ".ini"}
        or path.endswith(".env.example")
    ):
        return "configuration"
    if "test" in path.lower() or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    return "source"


def _shard_id(path: str) -> str:
    return (path.split("/", 1)[0] if "/" in path else "root").replace(".", "_")


def build_knowledge(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(output_dir).resolve() if output_dir else root / config["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "symbols").mkdir(exist_ok=True)
    # Agent-doc integration is intentionally part of a build; create it before
    # discovery so the snapshot cannot immediately mark itself stale.
    link_agent_docs(root, out)
    included, generated, ignored = discover_files(root, config)
    files: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    commands: list[dict[str, str]] = []
    configs: list[dict[str, Any]] = []
    unknowns: list[str] = []
    languages: set[str] = set()
    file_hashes: dict[str, str] = {}
    subsystems: dict[str, list[str]] = {}
    for path in included:
        full = root / path
        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            unknowns.append(f"Unreadable {path}: {exc}")
            continue
        if is_secret_file_or_content(full, content):
            ignored.append(path)
            continue
        role = _role(path)
        subsystem = path.split("/", 1)[0] if "/" in path else "root"
        suffix = full.suffix.lower()
        languages.add(LANGUAGES[suffix]) if suffix in LANGUAGES else None
        subsystems.setdefault(subsystem, []).append(path)
        raw_imports: list[str] = []
        extracted: list[Any] = []
        if suffix == ".py":
            extracted, raw_imports, _, unks = extract_python_file(full, path, content, subsystem)
            unknowns.extend(unks)
        elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
            extracted, raw_imports, _, unks = extract_javascript_file(full, path, content, subsystem)
            unknowns.extend(unks)
        elif suffix in {".go", ".rs", ".java", ".c", ".cpp"}:
            extracted, raw_imports, _, unks = extract_lexical_file(full, path, content, subsystem)
            unknowns.extend(unks)
        if role == "configuration":
            entry, found = extract_config_and_commands(root, path, content)
            configs.append(entry)
            commands.extend(found)
        file_hashes[path] = compute_file_hash(full)
        names: list[str] = []
        for item in extracted:
            names.append(item.name)
            symbols.append(
                {
                    "name": item.name,
                    "qualified_name": item.qualified_name,
                    "kind": item.kind,
                    "path": path,
                    "line_start": item.line_start,
                    "line_end": item.line_end,
                    "owner": subsystem,
                    "exported": not item.name.startswith("_"),
                    "docstring": item.docstring,
                }
            )
        files.append(
            {
                "path": path,
                "role": role,
                "subsystem": subsystem,
                "language": LANGUAGES.get(suffix, ""),
                "hash": file_hashes[path],
                "line_count": len(content.splitlines()),
                "symbols": sorted(names),
                "raw_imports": sorted(set(raw_imports)),
                "generated": path in generated,
            }
        )
    files.sort(key=lambda x: x["path"])
    symbols.sort(key=lambda x: (x["path"], x["line_start"], x["name"]))
    paths = {f["path"] for f in files}
    file_by_path = {f["path"]: f for f in files}
    imports: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    reverse: dict[str, list[str]] = {p: [] for p in paths}
    for f in files:
        for raw in f["raw_imports"]:
            target = resolve_import_to_path(raw, paths, f["path"])
            if target:
                imports.append(
                    {"source": f["path"], "target": target, "kind": "import", "confidence": "high", "evidence": [raw]}
                )
                reverse[target].append(f["path"])
            else:
                unresolved.append({"source": f["path"], "import": raw, "reason": "external-or-unresolved"})
    test_links: list[dict[str, str]] = []
    for f in files:
        if f["role"] == "test":
            candidates = [
                e["target"]
                for e in imports
                if e["source"] == f["path"] and file_by_path[e["target"]]["role"] == "source"
            ]
            stem = Path(f["path"]).stem.replace("test_", "").replace("_test", "")
            candidates += [p for p, x in file_by_path.items() if x["role"] == "source" and Path(p).stem == stem]
            for target in sorted(set(candidates)):
                test_links.append({"source": f["path"], "target": target, "kind": "test"})
    config_links = [
        {"source": cfg["path"], "target": p, "kind": "configuration", "confidence": "low"}
        for cfg in configs
        for p in []
    ]
    entry_points = [
        {"path": f["path"], "symbol": (f["symbols"][0] if f["symbols"] else "main"), "kind": "entry-point"}
        for f in files
        if Path(f["path"]).name.lower() in {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}
    ]
    repo_map = {
        "schema_version": SCHEMA_VERSION,
        "repository": {"root": ".", "languages": sorted(languages)},
        "subsystems": [{"name": name, "paths": sorted(value)} for name, value in sorted(subsystems.items())],
        "directories": [{"path": name, "file_count": len(value)} for name, value in sorted(subsystems.items())],
        "files": files,
        "entry_points": sorted(entry_points, key=lambda x: x["path"]),
        "commands": sorted(commands, key=lambda x: (x["kind"], x["cmd"])),
        "configurations": sorted(configs, key=lambda x: x["path"]),
        "generated_paths": sorted(generated),
        "ignored_paths": sorted(set(ignored)),
        "unknowns": sorted(unknowns)[:20],
    }
    relationships = {
        "schema_version": SCHEMA_VERSION,
        "imports": sorted(imports, key=lambda x: (x["source"], x["target"])),
        "calls": [],
        "test_links": test_links,
        "configuration_links": config_links,
        "unresolved_imports": sorted(unresolved, key=lambda x: (x["source"], x["import"])),
        "reverse_imports": {p: sorted(v) for p, v in sorted(reverse.items()) if v},
    }
    shards: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        shards.setdefault(_shard_id(symbol["path"]), []).append(symbol)
    catalog = {"schema_version": SCHEMA_VERSION, "symbol_count": len(symbols), "shards": []}
    for shard, entries in sorted(shards.items()):
        relative = f"symbols/{shard}.json"
        payload = {"schema_version": SCHEMA_VERSION, "shard": shard, "symbols": entries}
        encoded = serialize_json_deterministic(payload)
        write_file_deterministic(out / relative, encoded)
        catalog["shards"].append(
            {"id": shard, "path": relative, "count": len(entries), "hash": hashlib.sha256(encoded.encode()).hexdigest()}
        )
    revision, branch, dirty, untracked = get_git_info(root)
    artifact_payloads = {"repo-map.json": repo_map, "relationships.json": relationships, "symbols.json": catalog}
    artifact_hashes = {name: _digest(data) for name, data in artifact_payloads.items()}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "repository": {
            "root": ".",
            "revision": revision,
            "branch": branch,
            "dirty": dirty,
            "untracked_files": untracked,
        },
        "generation_mode": "full",
        "ignore_hash": _digest({k: config.get(k) for k in ("include", "exclude", "generated")}),
        "index_hash": _digest(artifact_hashes),
        "inventory_hash": _digest(file_hashes),
        "indexed_paths": sorted(paths),
        "file_hashes": file_hashes,
        "artifact_hashes": artifact_hashes,
        "changed_files": [],
        "freshness_state": "fresh",
    }
    errors = sum(
        (
            validate_schema_json(manifest, "manifest.schema.json"),
            validate_schema_json(repo_map, "repo-map.schema.json"),
            validate_schema_json(catalog, "symbols.schema.json"),
            validate_schema_json(relationships, "relationships.schema.json"),
            validate_semantic_graph(root, repo_map, relationships, symbols, manifest),
        ),
        [],
    )
    if errors:
        raise ValueError(f"Knowledge build validation failed: {errors}")
    for name, data in artifact_payloads.items():
        write_file_deterministic(out / name, serialize_json_deterministic(data))
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
    write_file_deterministic(
        out / "context.md",
        format_context_md(revision, subsystems, sorted(languages), entry_points, commands, unknowns=unknowns),
    )
    write_file_deterministic(
        out / "architecture.md",
        format_architecture_md(
            revision,
            subsystems,
            imports,
            [{"path": link["source"], "targets": [link["target"]]} for link in test_links],
            configs,
        ),
    )
    legacy = out / "index.json"
    if legacy.exists():
        legacy.unlink()
    workflow = ensure_github_workflow(
        root,
        config["workflow_branch"],
        config["workflow_runtime_repository"],
        config["workflow_runtime_revision"],
        config["workflow_runtime_directory"],
    )
    return {
        "status": "success",
        "output_dir": str(out),
        "files_indexed": len(files),
        "symbols_indexed": len(symbols),
        "index_hash": manifest["index_hash"],
        "workflow": workflow,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = build_knowledge(Path(args.repo_root), Path(args.output) if args.output else None)
    if not args.quiet:
        print(
            f"Build completed: {result['files_indexed']} files, {result['symbols_indexed']} symbols indexed -> {result['output_dir']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
