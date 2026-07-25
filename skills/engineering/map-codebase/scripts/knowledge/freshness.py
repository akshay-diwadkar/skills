"""Git-backed freshness checks and parity-preserving incremental refresh."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from build_knowledge import EXTRACTOR_VERSION, SCHEMA_VERSION, _config_hash, _digest, get_git_info
from knowledge.config import load_config, resolve_knowledge_directory
from knowledge.discovery import (
    discover_files,
    filter_internal_paths,
    git_tracked_paths,
    git_untracked_paths,
    is_internal_runtime_path,
    is_tracked_path,
    run_git,
)
from knowledge.indexing import classify_and_extract, is_repository_wide_config, project, shard_id
from knowledge.schemas import validate_schema_json
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic

REQUIRED = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json"]


def _git(root: Path, *args: str) -> str | None:
    result = run_git(root, *args, text=True)
    return result.stdout if result is not None else None


def _changed(text: str) -> set[str]:
    return {field.replace("\\", "/") for line in text.splitlines() for field in line.split("\t")[1:] if field}


def _git_changes(root: Path, revision: str, include_untracked: bool, output: Path) -> tuple[set[str], str, str] | None:
    """Return Git changes, current revision, and detection mode.

    ``None`` means Git itself is unavailable.  A failed diff with a usable HEAD
    is deliberately reported as inventory recovery rather than Git absence.
    """
    current = _git(root, "rev-parse", "HEAD")
    if current is None:
        return None
    outputs = [
        _git(root, "diff", "--find-renames", "--name-status", revision, "HEAD"),
        _git(root, "diff", "--find-renames", "--name-status"),
        _git(root, "diff", "--find-renames", "--name-status", "--cached"),
    ]
    untracked = _git(root, "ls-files", "--others", "--exclude-standard") if include_untracked else ""
    if any(value is None for value in outputs) or untracked is None:
        return set(), current.strip(), "git-inventory-recovery"
    changes = set().union(*(_changed(value or "") for value in outputs))
    changes.update(value.replace("\\", "/") for value in untracked.splitlines() if value)
    return set(filter_internal_paths(root, output, changes)), current.strip(), "git-diff"


def _repository_metadata(root: Path, config: dict[str, Any], output: Path) -> dict[str, Any]:
    """Compute metadata with only safely indexable untracked files represented."""
    revision, branch, dirty, _untracked = get_git_info(root, config, output)
    # Preserve repository-state metadata for all Git-visible untracked paths
    # when opt-in is enabled; this is intentionally separate from eligibility.
    relevant_untracked = (
        filter_internal_paths(root, output, git_untracked_paths(root)) if config.get("include_untracked", True) else []
    )
    return {
        "root": ".",
        "revision": revision,
        "branch": branch,
        "dirty": dirty,
        "untracked_files": sorted(relevant_untracked),
    }


def _inventory_changes(root: Path, config: dict[str, Any], manifest: dict[str, Any], output: Path) -> list[str]:
    """Compare eligible content hashes without relying on a diffable revision."""
    included, _, _ = discover_files(root, config, output)
    old = manifest.get("file_hashes", {})
    current = {path: item.record["hash"] for path in included if (item := classify_and_extract(root, path, config)[0])}
    return sorted(path for path in set(old) | set(current) if old.get(path) != current.get(path))


def _invalid(reason: str) -> dict[str, Any]:
    return {"status": "invalid", "reason": reason, "changed_files": [], "requires_full_rebuild": True}


def _load_root_artifacts(out: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | dict[str, Any]:
    if any(not (out / name).is_file() for name in REQUIRED):
        return {"status": "missing", "reason": "Required machine knowledge artifacts are missing.", "changed_files": [], "requires_full_rebuild": True}
    try:
        manifest, repo, catalog, relationships = [json.loads((out / name).read_text(encoding="utf-8")) for name in REQUIRED]
    except Exception as exc:
        return _invalid(f"Invalid root JSON: {exc}")
    for payload, schema, name in zip(
        (manifest, repo, catalog, relationships),
        ("manifest.schema.json", "repo-map.schema.json", "symbols.schema.json", "relationships.schema.json"),
        REQUIRED,
    ):
        if validate_schema_json(payload, schema):
            return _invalid(f"Root schema mismatch: {name}")
    for name, payload in (("repo-map.json", repo), ("symbols.json", catalog), ("relationships.json", relationships)):
        if manifest.get("artifact_hashes", {}).get(name) != _digest(payload):
            return _invalid(f"Artifact hash mismatch: {name}")
    for shard in catalog.get("shards", []):
        path = out / shard.get("path", "")
        if not path.is_file():
            return _invalid(f"Symbol shard missing: {shard.get('path', '')}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != shard.get("hash"):
            return _invalid(f"Shard hash mismatch: {shard.get('path', '')}")
    return manifest, repo, catalog, relationships


def check_freshness(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = resolve_knowledge_directory(root, knowledge_dir, config)
    loaded = _load_root_artifacts(out)
    if not isinstance(loaded, tuple):
        return loaded
    manifest, _repo, _catalog, _relationships = loaded
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("extractor_version") != EXTRACTOR_VERSION or manifest.get("config_hash") != _config_hash(config):
        return {"status": "stale", "reason": "Schema, extractor, or indexing configuration changed.", "changed_files": [], "requires_full_rebuild": True}
    state = _git_changes(root, manifest["repository"].get("revision", ""), config["include_untracked"], out)
    if state is None:
        fallback_changes = _inventory_changes(root, config, manifest, out)
        return {
            "status": "fresh" if not fallback_changes else "partially-stale",
            "reason": "Git unavailable; used inventory fallback.",
            "changed_files": fallback_changes,
            "requires_full_rebuild": False,
            "revision_changed": False,
            "detection_mode": "filesystem-inventory",
        }
    candidates, current_revision, detection_mode = state
    if detection_mode == "git-inventory-recovery":
        recovery_changes = _inventory_changes(root, config, manifest, out)
        metadata = _repository_metadata(root, config, out)
        return {
            "status": "fresh" if not recovery_changes else "partially-stale",
            "reason": "Recorded revision cannot be diffed; used inventory recovery.",
            "changed_files": recovery_changes,
            "requires_full_rebuild": bool(recovery_changes),
            "revision_changed": current_revision != manifest["repository"].get("revision"),
            "repository_metadata_changed": metadata != manifest.get("repository", {}),
            "current_revision": current_revision,
            "detection_mode": detection_mode,
        }
    tracked = git_tracked_paths(root)
    old = manifest.get("file_hashes", {})
    changes: set[str] = set()
    for path in candidates:
        if is_internal_runtime_path(root, out, path):
            continue
        tracked_path = is_tracked_path(root, path, tracked)
        if not config["include_untracked"] and not tracked_path:
            # A formerly indexed path that is now untracked must be removed;
            # brand-new untracked paths are invisible to this configuration.
            if path in old:
                changes.add(path)
            continue
        extracted, normalised, _reason = classify_and_extract(root, path, config)
        if extracted is None:
            if normalised in old:
                changes.add(normalised)
        elif extracted.record["hash"] != old.get(normalised):
            changes.add(normalised)
    metadata = _repository_metadata(root, config, out)
    revision_changed = current_revision != manifest["repository"].get("revision")
    repository_metadata_changed = metadata != manifest.get("repository", {})
    return {
        "status": "fresh" if not changes else "partially-stale",
        "reason": (
            "Updated repository revision without indexed content changes."
            if revision_changed and not changes
            else ("No relevant repository changes" if not changes else f"{len(changes)} repository changes.")
        ),
        "changed_files": sorted(changes),
        "requires_full_rebuild": False,
        "revision_changed": revision_changed,
        "repository_metadata_changed": repository_metadata_changed,
        "current_revision": current_revision,
        "detection_mode": detection_mode,
    }


def _normalise(root: Path, output: Path, paths: list[str]) -> list[str]:
    result = []
    for raw in paths:
        full = Path(raw).resolve() if Path(raw).is_absolute() else (root / raw).resolve()
        try:
            result.append(full.relative_to(root).as_posix())
        except ValueError as exc:
            raise ValueError(f"Changed path is outside repository: {raw}") from exc
    return filter_internal_paths(root, output, result)


def _metadata_only(root: Path, out: Path, manifest: dict[str, Any], config: dict[str, Any]) -> None:
    manifest.update(
        {
            "generation_mode": "metadata-only",
            "repository": _repository_metadata(root, config, out),
            "changed_files": [],
            "freshness_state": "fresh",
        }
    )
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))


def refresh_knowledge(repo_root: Path | str, changed_files: list[str] | None = None, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = resolve_knowledge_directory(root, knowledge_dir, config)
    state = check_freshness(root, out)
    if state.get("requires_full_rebuild"):
        from build_knowledge import build_knowledge

        return {
            "mode": "full",
            "status": "fresh",
            "reason": state.get("reason", "Full rebuild required."),
            "changed_files": state.get("changed_files", []),
            "details": build_knowledge(root, out),
        }
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    tracked = git_tracked_paths(root)
    explicit = _normalise(root, out, changed_files or [])
    explicit = [
        path
        for path in explicit
        if config["include_untracked"] or is_tracked_path(root, path, tracked) or path in manifest.get("file_hashes", {})
    ]
    changes = sorted(set(explicit) | set(state.get("changed_files", [])))
    if any(is_repository_wide_config(path) for path in changes):
        from build_knowledge import build_knowledge
        return {
            "mode": "full",
            "status": "fresh",
            "reason": state.get("reason", "Repository-wide configuration changed."),
            "changed_files": changes,
            "details": build_knowledge(root, out),
        }
    if not changes:
        if state.get("repository_metadata_changed"):
            _metadata_only(root, out, manifest, config)
            return {"mode": "metadata-only", "status": "fresh", "reason": "Updated repository metadata without indexed content changes.", "changed_files": []}
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh.", "changed_files": []}
    if len(manifest.get("indexed_paths", [])) > 10 and len(changes) / len(manifest["indexed_paths"]) > config["full_refresh_change_ratio"]:
        from build_knowledge import build_knowledge
        return {"mode": "full", "status": "fresh", "reason": "Changed-path ratio exceeds configured safe delta threshold.", "changed_files": changes, "details": build_knowledge(root, out)}
    _apply_delta(root, out, config, changes)
    return {"mode": "incremental", "status": "fresh", "reason": "Applied shared file-level extraction and projection.", "changed_files": changes}


def _apply_delta(root: Path, out: Path, config: dict[str, Any], changes: list[str]) -> None:
    loaded = _load_root_artifacts(out)
    if not isinstance(loaded, tuple):
        raise ValueError(loaded["reason"])
    manifest, old_repo, catalog, _ = loaded
    files = {item["path"]: item for item in old_repo["files"]}
    configs = {item["path"]: item for item in old_repo.get("configurations", [])}
    shards = {item["id"]: item for item in catalog["shards"]}
    affected = {shard_id(path) for path in changes}
    shard_symbols = {
        key: json.loads((out / shards[key]["path"]).read_text(encoding="utf-8"))["symbols"] if key in shards else []
        for key in affected
    }
    for path in changes:
        files.pop(path, None)
        configs.pop(path, None)
        key = shard_id(path)
        shard_symbols[key] = [item for item in shard_symbols[key] if item["path"] != path]
        extracted, _normalised_path, _reason = classify_and_extract(root, path, config)
        if extracted:
            files[extracted.record["path"]] = extracted.record
            shard_symbols[key].extend(extracted.symbols)
            if extracted.configuration:
                configs[extracted.record["path"]] = extracted.configuration
    commands = []
    for path in sorted(configs):
        extracted = classify_and_extract(root, path, config)[0]
        if extracted:
            commands.extend(extracted.commands)
    repo, relationships = project(list(files.values()), list(configs.values()), commands)
    _included, _generated, current_ignored = discover_files(root, config, out)
    current_ignored = filter_internal_paths(root, out, current_ignored)
    repo["ignored_paths"] = sorted((set(old_repo.get("ignored_paths", [])) - set(changes)) | set(current_ignored))
    for key in affected:
        entries = sorted(shard_symbols[key], key=lambda item: (item["path"], item["line_start"], item["name"]))
        shard_path = out / f"symbols/{key}.json"
        if entries:
            encoded = serialize_json_deterministic({"schema_version": SCHEMA_VERSION, "shard": key, "symbols": entries})
            write_file_deterministic(shard_path, encoded)
            shards[key] = {"id": key, "path": f"symbols/{key}.json", "count": len(entries), "hash": hashlib.sha256(encoded.encode()).hexdigest()}
        else:
            if shard_path.exists():
                shard_path.unlink()
            shards.pop(key, None)
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "symbol_count": sum(item["count"] for item in shards.values()),
        "shards": [shards[key] for key in sorted(shards)],
    }
    artifacts = {"repo-map.json": repo, "relationships.json": relationships, "symbols.json": catalog}
    for name, data in artifacts.items():
        write_file_deterministic(out / name, serialize_json_deterministic(data))
    metadata = _repository_metadata(root, config, out)
    file_hashes = {item["path"]: item["hash"] for item in files.values()}
    hashes = {name: _digest(data) for name, data in artifacts.items()}
    manifest.update({"schema_version": SCHEMA_VERSION, "extractor_version": EXTRACTOR_VERSION, "repository": metadata, "generation_mode": "incremental", "config_hash": _config_hash(config), "index_hash": _digest(hashes), "inventory_hash": _digest(file_hashes), "indexed_paths": sorted(file_hashes), "file_hashes": file_hashes, "artifact_hashes": hashes, "changed_files": changes, "freshness_state": "fresh"})
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
