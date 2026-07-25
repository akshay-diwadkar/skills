"""Git-backed freshness checks and parity-preserving incremental refresh."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from build_knowledge import EXTRACTOR_VERSION, SCHEMA_VERSION, _config_hash, _digest, get_git_info
from knowledge.config import load_config
from knowledge.discovery import discover_files
from knowledge.indexing import classify_and_extract, is_repository_wide_config, project, shard_id
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic

REQUIRED = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json"]


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _changed(text: str) -> set[str]:
    result = set()
    for line in text.splitlines():
        fields = line.split("\t")
        result.update(field.replace("\\", "/") for field in fields[1:] if field)
    return result


def _git_changes(root: Path, revision: str) -> tuple[set[str], str] | None:
    current = _git(root, "rev-parse", "HEAD")
    if current is None:
        return None
    outputs = [
        _git(root, "diff", "--find-renames", "--name-status", revision, "HEAD"),
        _git(root, "diff", "--find-renames", "--name-status"),
        _git(root, "diff", "--find-renames", "--cached", "--name-status"),
    ]
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if any(x is None for x in outputs) or untracked is None:
        return None
    changes = set().union(*(_changed(x or "") for x in outputs))
    changes.update(x.replace("\\", "/") for x in untracked.splitlines() if x)
    return changes, current.strip()


def check_freshness(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]
    if any(not (out / name).is_file() for name in REQUIRED):
        return {
            "status": "missing",
            "reason": "Required machine knowledge artifacts are missing.",
            "changed_files": [],
            "requires_full_rebuild": True,
        }
    try:
        manifest = json.loads((out / "manifest.json").read_text())
        catalog = json.loads((out / "symbols.json").read_text())
    except Exception as exc:
        return {"status": "invalid", "reason": str(exc), "changed_files": [], "requires_full_rebuild": True}
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("extractor_version") != EXTRACTOR_VERSION
        or manifest.get("config_hash") != _config_hash(config)
    ):
        return {
            "status": "stale",
            "reason": "Schema, extractor, or indexing configuration changed.",
            "changed_files": [],
            "requires_full_rebuild": True,
        }
    if any(not (out / x["path"]).is_file() for x in catalog.get("shards", [])):
        return {
            "status": "invalid",
            "reason": "Symbol shard missing.",
            "changed_files": [],
            "requires_full_rebuild": True,
        }
    state = _git_changes(root, manifest["repository"].get("revision", ""))
    if state is None:
        included, _, _ = discover_files(root, config)
        old = manifest.get("file_hashes", {})
        current = {}
        for path in included:
            item, _, _ = classify_and_extract(root, path, config)
            if item:
                current[path] = item.record["hash"]
        changes = sorted(path for path in set(old) | set(current) if old.get(path) != current.get(path))
        return {
            "status": "fresh" if not changes else "partially-stale",
            "reason": "Git unavailable; used inventory fallback.",
            "changed_files": changes,
            "requires_full_rebuild": False,
        }
    candidates, current = state
    output_rel = out.relative_to(root).as_posix()
    old = manifest.get("file_hashes", {})
    changes = set()
    for path in candidates:
        if path == output_rel or path.startswith(output_rel + "/"):
            continue
        item, normalised, _ = classify_and_extract(root, path, config)
        if item is None:
            if normalised in old:
                changes.add(normalised)
        elif item.record["hash"] != old.get(normalised):
            changes.add(normalised)
    # Keep excluded/secret paths in the delta so refresh can remove old records safely.
    return {
        "status": "fresh" if not changes else "partially-stale",
        "reason": "No relevant repository changes" if not changes else f"{len(changes)} repository changes.",
        "changed_files": sorted(changes),
        "requires_full_rebuild": False,
    }


def _normalise(root: Path, paths: list[str]) -> list[str]:
    result = []
    for raw in paths:
        full = Path(raw).resolve() if Path(raw).is_absolute() else (root / raw).resolve()
        try:
            result.append(full.relative_to(root).as_posix())
        except ValueError as exc:
            raise ValueError(f"Changed path is outside repository: {raw}") from exc
    return sorted(set(result))


def refresh_knowledge(
    repo_root: Path | str, changed_files: list[str] | None = None, knowledge_dir: Path | str | None = None
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]
    explicit = _normalise(root, changed_files or [])
    state = check_freshness(root, out)
    changes = sorted(set(explicit) | set(state.get("changed_files", [])))
    if state.get("requires_full_rebuild") or any(is_repository_wide_config(p) for p in changes):
        from build_knowledge import build_knowledge

        result = build_knowledge(root, out)
        return {
            "mode": "full",
            "status": "fresh",
            "reason": state.get("reason", "Repository-wide configuration changed."),
            "changed_files": changes,
            "details": result,
        }
    if not changes:
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh.", "changed_files": []}
    manifest = json.loads((out / "manifest.json").read_text())
    if (
        len(manifest.get("indexed_paths", [])) > 10
        and len(changes) / len(manifest["indexed_paths"]) > config["full_refresh_change_ratio"]
    ):
        from build_knowledge import build_knowledge

        return {
            "mode": "full",
            "status": "fresh",
            "reason": "Changed-path ratio exceeds configured safe delta threshold.",
            "changed_files": changes,
            "details": build_knowledge(root, out),
        }
    _apply_delta(root, out, config, changes)
    return {
        "mode": "incremental",
        "status": "fresh",
        "reason": "Applied shared file-level extraction and projection.",
        "changed_files": changes,
    }


def _apply_delta(root: Path, out: Path, config: dict[str, Any], changes: list[str]) -> None:
    manifest = json.loads((out / "manifest.json").read_text())
    old_repo = json.loads((out / "repo-map.json").read_text())
    catalog = json.loads((out / "symbols.json").read_text())
    files = {x["path"]: x for x in old_repo["files"]}
    configs = {x["path"]: x for x in old_repo.get("configurations", [])}
    old_shards = {x["id"]: x for x in catalog["shards"]}
    affected = {shard_id(path) for path in changes}
    shard_symbols = {}
    for key in affected:
        item = old_shards.get(key)
        shard_symbols[key] = json.loads((out / item["path"]).read_text())["symbols"] if item else []
    unknowns = []
    commands = []
    for path in changes:
        files.pop(path, None)
        configs.pop(path, None)
        key = shard_id(path)
        shard_symbols[key] = [x for x in shard_symbols[key] if x["path"] != path]
        item, normalised, reason = classify_and_extract(root, path, config)
        if item is None:
            if reason:
                unknowns.append(f"Skipped {normalised}: {reason}")
            continue
        files[item.record["path"]] = item.record
        shard_symbols[key].extend(item.symbols)
        unknowns.extend(item.unknowns)
        if item.configuration:
            configs[item.record["path"]] = item.configuration
    # Commands must be recomputed from current configuration records to avoid stale values.
    for path in sorted(configs):
        item, _, _ = classify_and_extract(root, path, config)
        if item:
            commands.extend(item.commands)
    repo, relationships = project(
        list(files.values()), list(configs.values()), commands, list(old_repo.get("unknowns", [])) + unknowns
    )
    repo["ignored_paths"] = sorted(set(old_repo.get("ignored_paths", [])) | {p for p in changes if p not in files})
    for key in affected:
        entries = sorted(shard_symbols[key], key=lambda x: (x["path"], x["line_start"], x["name"]))
        path = out / f"symbols/{key}.json"
        if entries:
            encoded = serialize_json_deterministic({"schema_version": SCHEMA_VERSION, "shard": key, "symbols": entries})
            write_file_deterministic(path, encoded)
            old_shards[key] = {
                "id": key,
                "path": f"symbols/{key}.json",
                "count": len(entries),
                "hash": hashlib.sha256(encoded.encode()).hexdigest(),
            }
        else:
            if path.exists():
                path.unlink()
            old_shards.pop(key, None)
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "symbol_count": sum(x["count"] for x in old_shards.values()),
        "shards": [old_shards[x] for x in sorted(old_shards)],
    }
    artifacts = {"repo-map.json": repo, "relationships.json": relationships, "symbols.json": catalog}
    for name, data in artifacts.items():
        write_file_deterministic(out / name, serialize_json_deterministic(data))
    revision, branch, dirty, untracked = get_git_info(root)
    hashes = {name: _digest(data) for name, data in artifacts.items()}
    file_hashes = {x["path"]: x["hash"] for x in files.values()}
    manifest.update(
        {
            "schema_version": SCHEMA_VERSION,
            "extractor_version": EXTRACTOR_VERSION,
            "repository": {
                "root": ".",
                "revision": revision,
                "branch": branch,
                "dirty": dirty,
                "untracked_files": untracked,
            },
            "generation_mode": "incremental",
            "config_hash": _config_hash(config),
            "index_hash": _digest(hashes),
            "inventory_hash": _digest(file_hashes),
            "indexed_paths": sorted(file_hashes),
            "file_hashes": file_hashes,
            "artifact_hashes": hashes,
            "changed_files": changes,
            "freshness_state": "fresh",
        }
    )
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
