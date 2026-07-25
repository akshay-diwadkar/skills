#!/usr/bin/env python3
"""Build deterministic, sharded repository knowledge artifacts."""

from __future__ import annotations

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
from knowledge.discovery import discover_files, git_untracked_paths
from knowledge.indexing import classify_and_extract, project, shard_id
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic

SCHEMA_VERSION = "4.0"
EXTRACTOR_VERSION = "4.1.0"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get_git_info(
    root: Path, config: dict[str, Any] | None = None, indexed_paths: set[str] | None = None
) -> tuple[str, str, bool, list[str]]:
    """Return repository metadata using the same untracked policy as indexing."""
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    untracked = git_untracked_paths(root) if config is None or config.get("include_untracked", True) else []
    # Metadata records Git-visible untracked paths when enabled, including paths
    # excluded from indexing.  This lets a manifest reflect repository state
    # without granting those paths eligibility for extraction.
    return (
        git("rev-parse", "HEAD") or "unknown",
        git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        bool(git("status", "--porcelain")),
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


def build_knowledge(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(output_dir).resolve() if output_dir else root / config["output_dir"]
    try:
        out.relative_to(root)
    except ValueError:
        raise ValueError("knowledge output must be inside repository")
    out.mkdir(parents=True, exist_ok=True)
    (out / "symbols").mkdir(exist_ok=True)
    included, _, ignored = discover_files(root, config)
    output_prefix = out.relative_to(root).as_posix()
    ignored = [path for path in ignored if path != output_prefix and not path.startswith(output_prefix + "/")]
    files = []
    symbols = []
    configs = []
    commands = []
    for path in included:
        item, _, reason = classify_and_extract(root, path, config)
        if item is None:
            ignored.append(path)
            continue
        files.append(item.record)
        symbols.extend(item.symbols)
        if item.configuration:
            configs.append(item.configuration)
        commands.extend(item.commands)
    repo, relationships = project(files, configs, commands)
    repo["ignored_paths"] = sorted(set(ignored))
    catalog = _write_shards(out, symbols)
    artifacts = {"repo-map.json": repo, "relationships.json": relationships, "symbols.json": catalog}
    hashes = {name: _digest(data) for name, data in artifacts.items()}
    file_hashes = {f["path"]: f["hash"] for f in files}
    revision, branch, dirty, untracked = get_git_info(root, config, set(file_hashes))
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
    for old in (out / "context.md", out / "architecture.md", out / "index.json"):
        if old.exists():
            old.unlink()
    return {
        "status": "success",
        "output_dir": str(out),
        "files_indexed": len(files),
        "symbols_indexed": len(symbols),
        "index_hash": manifest["index_hash"],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    build_knowledge(args.repo_root, args.output)
