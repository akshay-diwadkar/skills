#!/usr/bin/env python3
"""Build deterministic, sharded repository knowledge artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config, resolve_knowledge_directory
from link_agent_docs import ensure_knowledge_guide
from knowledge.discovery import (
    discover_files,
    filter_internal_paths,
    git_file_states,
    git_tracked_paths,
    git_untracked_paths,
    is_internal_runtime_path,
    run_git,
)
from knowledge.fingerprint import compute_file_hash
from knowledge.indexing import IndexedFile, classify_and_extract, project, shard_id
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic

SCHEMA_VERSION = "6.0"
EXTRACTOR_VERSION = "6.0.0"
EVIDENCE_SHARD_VERSION = "1"
EVIDENCE_CACHE_FILE_LIMIT = 1_000


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get_git_info(root: Path, config: dict[str, Any] | None, output_dir: Path) -> tuple[str, str, bool, list[str]]:
    """Return repository metadata using the same untracked policy as indexing."""
    output = output_dir.resolve()

    def git(*args: str) -> str:
        result = run_git(root, *args, text=True)
        return result.stdout if result is not None else ""

    include_untracked = config is None or config.get("include_untracked", True)
    untracked = (
        filter_internal_paths(root, output, git_untracked_paths(root)) if include_untracked else []
    )
    # Porcelain v2 preserves index/working-tree state and --no-optional-locks
    # avoids refreshing an intentionally stale index.
    status_args = (
        "--no-optional-locks", "status", "--porcelain=v2", "-z",
        "--untracked-files=all" if include_untracked else "--untracked-files=no",
    )
    records = [record for record in git(*status_args).split("\0") if record]
    dirty_paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if record.startswith("? "):
            dirty_paths.append(record[2:])
        elif record.startswith(("1 ", "2 ")):
            dirty_paths.append(record.split(" ")[-1])
            if record.startswith("2 ") and index < len(records):
                index += 1
    dirty_lines = [path for path in dirty_paths if not is_internal_runtime_path(root, output, path)]
    # Metadata records Git-visible untracked paths when enabled, including paths
    # excluded from indexing.  This lets a manifest reflect repository state
    # without granting those paths eligibility for extraction.
    return (
        git("rev-parse", "HEAD").strip() or "unknown",
        git("rev-parse", "--abbrev-ref", "HEAD").strip() or "unknown",
        bool(dirty_lines),
        sorted(untracked),
    )


def _config_hash(config: dict[str, Any]) -> str:
    return _digest(
        {
            key: config.get(key)
            for key in ("include", "exclude", "generated", "max_file_size_bytes", "include_untracked", "confidence_margin", "weights")
        }
    )


def _write_shards(out: Path, symbols: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        grouped.setdefault(shard_id(symbol["path"]), []).append(symbol)
    shards = []
    for key, entries in sorted(grouped.items()):
        encoded = serialize_json_deterministic(
            {
                "schema_version": SCHEMA_VERSION,
                "shard": key,
                "symbols": sorted(entries, key=lambda x: (x["path"], x["line_start"], x["name"])),
            }
        )
        relative = f"symbols/{key}.json"
        write_file_deterministic(out / relative, encoded)
        shards.append(
            {"id": key, "path": relative, "count": len(entries), "hash": hashlib.sha256(encoded.encode()).hexdigest()}
        )
    expected = {item["path"] for item in shards}
    shard_dir = out / "symbols"
    for candidate in shard_dir.glob("*.json"):
        if candidate.relative_to(out).as_posix() not in expected:
            candidate.unlink()
    return {"schema_version": SCHEMA_VERSION, "symbol_count": len(symbols), "shards": shards}


def _symbol_index_payload(symbols: list[dict[str, Any]]) -> dict[str, Any]:
    """Return an inverted symbol index with deterministic entries."""
    index: dict[str, list[dict[str, Any]]] = {}
    for sym in symbols:
        entry = {
            "file": sym["path"],
            "line": sym["line_start"],
            "kind": sym["kind"],
            "qualified_name": sym.get("qualified_name", ""),
            "component_types": sym.get("component_types", []),
        }
        index.setdefault(sym["name"].lower(), []).append(entry)
    for sym in symbols:
        qname = sym.get("qualified_name", "").lower()
        if qname and qname != sym["name"].lower():
            entry = {
                "file": sym["path"],
                "line": sym["line_start"],
                "kind": sym["kind"],
                "qualified_name": sym.get("qualified_name", ""),
                "component_types": sym.get("component_types", []),
            }
            index.setdefault(qname, []).append(entry)
    for key in index:
        index[key] = sorted(index[key], key=lambda x: (x["file"], x["line"]))
    return {"schema_version": SCHEMA_VERSION, "symbols": dict(sorted(index.items()))}


def _evidence_key(record: dict[str, Any]) -> str:
    """Return a content-addressed raw-evidence shard key."""
    language = str(record.get("language") or "plain").lower().replace(" ", "-")
    return f"{record['hash']}-{language}-v{EXTRACTOR_VERSION}-e{EVIDENCE_SHARD_VERSION}"


def _load_cached_evidence(out: Path, path: str, file_hash: str) -> IndexedFile | None:
    """Reuse the exact prior extraction for unchanged content at the same path."""
    if not file_hash:
        return None
    for candidate in sorted((out / "evidence").glob(f"{file_hash}-*-v{EXTRACTOR_VERSION}-e{EVIDENCE_SHARD_VERSION}.json")):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("path") != path or payload.get("file_hash") != file_hash:
            continue
        record = payload.get("record")
        if isinstance(record, dict):
            return IndexedFile(record, payload.get("symbols", []), payload.get("configuration"), payload.get("commands", []), payload.get("unknowns", []))
    return None


def _write_evidence_shard(out: Path, item: IndexedFile) -> dict[str, Any]:
    key = _evidence_key(item.record)
    relative = f"evidence/{key}.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "evidence_shard_version": EVIDENCE_SHARD_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "path": item.record["path"],
        "file_hash": item.record["hash"],
        "record": item.record,
        "symbols": item.symbols,
        "configuration": item.configuration,
        "commands": item.commands,
        "unknowns": item.unknowns,
    }
    encoded = serialize_json_deterministic(payload)
    write_file_deterministic(out / relative, encoded)
    return {"path": item.record["path"], "shard": relative, "hash": hashlib.sha256(encoded.encode()).hexdigest()}


def _prune_evidence_shards(out: Path, retained: set[str]) -> None:
    for candidate in (out / "evidence").glob("*.json"):
        if candidate.relative_to(out).as_posix() not in retained:
            candidate.unlink()


def build_knowledge(
    repo_root: Path | str, output_dir: Path | str | None = None, *, worker_count: int | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = resolve_knowledge_directory(root, output_dir, config)
    out.mkdir(parents=True, exist_ok=True)
    (out / "symbols").mkdir(exist_ok=True)
    (out / "evidence").mkdir(exist_ok=True)
    included, _, ignored = discover_files(root, config, out)
    cache_evidence = len(included) <= EVIDENCE_CACHE_FILE_LIMIT
    ignored = filter_internal_paths(root, out, ignored)
    tracked_paths = git_tracked_paths(root)
    git_states = git_file_states(root)
    files = []
    symbols = []
    configs = []
    commands = []
    skipped_errors: list[tuple[str, str]] = []
    evidence_index: list[dict[str, Any]] = []
    # File extraction is independent per path. ``executor.map`` preserves the
    # discovery order, so parallel I/O and parser work cannot change emitted
    # artifacts or error reporting order.
    # Parsing many small files is GIL- and filesystem-contention bound on
    # Windows. Eight workers keeps large repository builds faster and more
    # stable than the previous sixteen-way fan-out.
    workers = worker_count if worker_count is not None else min(8, max(1, os.cpu_count() or 1))
    if workers < 1:
        raise ValueError("worker_count must be at least 1")
    def extract(path: str) -> tuple[str, Any, str | None, Exception | None]:
        try:
            cached = (
                _load_cached_evidence(out, path, compute_file_hash(root / path))
                if cache_evidence
                else None
            )
            if cached is not None:
                return path, cached, None, None
            item, _, reason = classify_and_extract(root, path, config)
        except (OSError, TimeoutError) as exc:
            return path, None, None, exc
        return path, item, reason, None

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="map-index") as executor:
        extracted_paths = executor.map(extract, included)
        for path, item, reason, error in extracted_paths:
            if error is not None:
                skipped_errors.append((path, str(error)))
                ignored.append(path)
                continue
            if item is None:
                ignored.append(path)
                continue
            state = git_states.get(path, {})
            item.record["tracked"] = path in tracked_paths if tracked_paths is not None else True
            item.record["git_state"] = {
                "index": bool(state.get("index", False)),
                "worktree": bool(state.get("worktree", False)),
                "untracked": bool(state.get("untracked", False)),
            }
            files.append(item.record)
            symbols.extend(item.symbols)
            if cache_evidence:
                evidence_index.append(_write_evidence_shard(out, item))
            if item.configuration:
                configs.append(item.configuration)
            commands.extend(item.commands)
    if skipped_errors:
        detail = "; ".join(f"{path}: {reason}" for path, reason in skipped_errors)
        print(f"Warning: {len(skipped_errors)} file(s) skipped after I/O or timeout failures: {detail}", file=sys.stderr)
    _prune_evidence_shards(out, {entry["shard"] for entry in evidence_index})
    repo, relationships = project(files, configs, commands)
    repo["ignored_paths"] = sorted(set(ignored))
    catalog = _write_shards(out, symbols)
    symbol_index = _symbol_index_payload(symbols)
    artifacts = {
        "repo-map.json": repo,
        "relationships.json": relationships,
        "symbols.json": catalog,
        "symbol-index.json": symbol_index,
        "evidence-index.json": {"schema_version": SCHEMA_VERSION, "shards": sorted(evidence_index, key=lambda entry: entry["path"])},
    }
    hashes = {name: _digest(data) for name, data in artifacts.items()}
    file_hashes = {f["path"]: f["hash"] for f in files}
    revision, branch, dirty, untracked = get_git_info(root, config, out)
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
        "ignore_hash": _digest({key: config.get(key) for key in ("include", "exclude", "generated")}),
        "config_hash": _config_hash(config),
        "index_hash": _digest(hashes),
        "inventory_hash": _digest(file_hashes),
        "indexed_paths": sorted(file_hashes),
        "file_hashes": file_hashes,
        "artifact_hashes": hashes,
        "changed_files": [],
        "freshness_state": "fresh",
    }
    errors = sum(
        (
            validate_schema_json(manifest, "manifest.schema.json"),
            validate_schema_json(repo, "repo-map.schema.json"),
            validate_schema_json(catalog, "symbols.schema.json"),
            validate_schema_json(symbol_index, "symbol-index.schema.json"),
            validate_schema_json(relationships, "relationships.schema.json"),
            validate_semantic_graph(root, repo, relationships, symbols, manifest),
        ),
        [],
    )
    if errors:
        raise ValueError(f"Knowledge build validation failed: {errors}")
    for name, data in artifacts.items():
        write_file_deterministic(out / name, serialize_json_deterministic(data))
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
    ensure_knowledge_guide(out)
    for old in (out / "context.md", out / "architecture.md", out / "index.json"):
        if old.exists():
            old.unlink()
    return {
        "_meta": {"command": "build"},
        "status": "success",
        "output_dir": str(out),
        "files_indexed": len(files),
        "symbols_indexed": len(symbols),
        "index_hash": manifest["index_hash"],
    }


if __name__ == "__main__":
    import argparse
    import json
    import sys

    from finalize_knowledge import KnowledgeFinalizationError, build_and_finalize

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()
    try:
        result = build_and_finalize(args.repo_root, args.output)
    except KnowledgeFinalizationError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Build completed: {result['files_indexed']} files, {result['symbols_indexed']} symbols indexed.")
