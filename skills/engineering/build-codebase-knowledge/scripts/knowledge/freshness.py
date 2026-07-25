"""Cheap Git-backed freshness checks and truthful delta refresh."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from knowledge.config import load_config
from knowledge.discovery import discover_files, is_secret_file_or_content, matches_glob
from knowledge.fingerprint import compute_file_hash
from knowledge.schemas import validate_schema_json
from knowledge.serialization import serialize_json_deterministic, write_file_deterministic

SCHEMA_VERSION = "2.0"
EXTRACTOR_VERSION = "3.0.0"
REQUIRED = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json", "context.md", "architecture.md"]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _changed_from_name_status(text: str) -> set[str]:
    paths: set[str] = set()
    for line in text.splitlines():
        fields = line.split("\t")
        if not fields:
            continue
        # Rename/copy output has old and new paths; both must be considered.
        paths.update(field.replace("\\", "/") for field in fields[1:] if field)
    return paths


def _git_changes(root: Path, revision: str) -> tuple[set[str], str] | None:
    current = _git(root, "rev-parse", "HEAD")
    if current is None:
        return None
    current = current.strip()
    if not revision or revision == "unknown":
        return set(), current
    outputs = [_git(root, "diff", "--name-status", revision, "HEAD"), _git(root, "diff", "--name-status"), _git(root, "diff", "--cached", "--name-status")]
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if any(item is None for item in outputs) or untracked is None:
        return None
    paths: set[str] = set()
    for output in outputs:
        paths.update(_changed_from_name_status(output or ""))
    paths.update(line.replace("\\", "/") for line in untracked.splitlines() if line)
    return paths, current


def _config_hash(config: dict[str, Any]) -> str:
    return _digest({key: config.get(key) for key in ("include", "exclude", "generated", "max_file_size_bytes", "weights")})


def check_freshness(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]
    if any(not (out / name).is_file() for name in REQUIRED):
        return {"status": "missing", "reason": "Required knowledge artifacts are missing.", "changed_files": [], "requires_full_rebuild": True}
    try:
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        catalog = json.loads((out / "symbols.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "invalid", "reason": str(exc), "changed_files": [], "requires_full_rebuild": True}
    if validate_schema_json(manifest, "manifest.schema.json") or any(not (out / shard["path"]).is_file() for shard in catalog.get("shards", [])):
        return {"status": "invalid", "reason": "Manifest/schema or symbol shard invalid.", "changed_files": [], "requires_full_rebuild": True}
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("extractor_version") != EXTRACTOR_VERSION:
        return {"status": "stale", "reason": "Schema or extractor version changed.", "changed_files": [], "requires_full_rebuild": True}
    if manifest.get("config_hash", manifest.get("ignore_hash")) != _config_hash(config):
        return {"status": "stale", "reason": "Indexing configuration or discovery rules changed.", "changed_files": [], "requires_full_rebuild": True}
    git_state = _git_changes(root, manifest.get("repository", {}).get("revision", ""))
    if git_state is None:
        # This is intentionally explicit: only the fallback can scan the inventory.
        included, _, _ = discover_files(root, config)
        current = {path: compute_file_hash(root / path) for path in included if (root / path).is_file()}
        changed = sorted(path for path in set(current) | set(manifest.get("file_hashes", {})) if current.get(path) != manifest.get("file_hashes", {}).get(path))
        return {"status": "fresh" if not changed else "partially-stale", "reason": "Git unavailable; used full inventory fallback.", "changed_files": changed, "requires_full_rebuild": False, "fallback": "inventory"}
    candidates, current_revision = git_state
    old_hashes = manifest.get("file_hashes", {})
    try:
        output_relative = out.relative_to(root).as_posix()
    except ValueError:
        output_relative = ""
    changed: list[str] = []
    for path in sorted(candidates):
        if (output_relative and (path == output_relative or path.startswith(output_relative + "/"))) or matches_glob(path, config.get("exclude", [])):
            continue
        full = root / path
        if not full.exists():
            if path in old_hashes:
                changed.append(path)
            continue
        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
            if not is_secret_file_or_content(full, content) and compute_file_hash(full) != old_hashes.get(path):
                changed.append(path)
        except OSError:
            changed.append(path)
    if current_revision != manifest.get("repository", {}).get("revision") and not changed:
        return {"status": "partially-stale", "reason": "Repository revision changed without indexed file changes.", "changed_files": [], "requires_full_rebuild": False}
    return {"status": "fresh" if not changed else "partially-stale", "reason": "No relevant repository changes" if not changed else f"{len(changed)} relevant repository changes.", "changed_files": changed, "requires_full_rebuild": False}


def refresh_knowledge(repo_root: Path | str, changed_files: list[str] | None = None, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    """Apply a safe delta. Only modified source paths and their shards are rewritten."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]
    explicit = _normalise_changed(root, changed_files or [])
    state = check_freshness(root, out)
    if state["status"] == "fresh" and not explicit:
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh.", "changed_files": []}
    if state.get("requires_full_rebuild"):
        from build_knowledge import build_knowledge
        result = build_knowledge(root, out)
        return {"mode": "full", "status": "fresh", "reason": state["reason"], "changed_files": explicit or state.get("changed_files", []), "details": result}
    changes = explicit or state.get("changed_files", [])
    if not changes:
        return _refresh_revision_only(root, out, config)
    # A very large delta is safer and cheaper to rebuild as a whole.
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest.get("indexed_paths", [])) > 10 and len(changes) / len(manifest["indexed_paths"]) > config["full_refresh_change_ratio"]:
        from build_knowledge import build_knowledge
        result = build_knowledge(root, out)
        return {"mode": "full", "status": "fresh", "reason": "Changed-path ratio exceeds configured safe delta threshold.", "changed_files": changes, "details": result}
    _apply_delta(root, out, config, changes)
    return {"mode": "incremental", "status": "fresh", "reason": "Applied file-level delta.", "changed_files": changes}


def _normalise_changed(root: Path, paths: list[str]) -> list[str]:
    normalised: list[str] = []
    for raw in paths:
        path = Path(raw)
        full = path.resolve() if path.is_absolute() else (root / path).resolve()
        try:
            normalised.append(full.relative_to(root).as_posix())
        except ValueError as exc:
            raise ValueError(f"Changed path is outside repository: {raw}") from exc
    return sorted(set(normalised))


def _refresh_revision_only(root: Path, out: Path, config: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    revision = (_git(root, "rev-parse", "HEAD") or "unknown").strip()
    manifest["repository"]["revision"] = revision
    manifest["generation_mode"] = "incremental"
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
    return {"mode": "incremental", "status": "fresh", "reason": "Updated repository revision metadata.", "changed_files": []}


def _apply_delta(root: Path, out: Path, config: dict[str, Any], changes: list[str]) -> None:
    """Patch file records and shards; relationship/summaries are deterministic projections."""
    from build_knowledge import LANGUAGES, _role, _shard_id, get_git_info
    from knowledge.extraction.configuration import extract_config_and_commands
    from knowledge.extraction.javascript import extract_javascript_file
    from knowledge.extraction.lexical import extract_lexical_file
    from knowledge.extraction.python import extract_python_file
    from knowledge.relationships import resolve_import_to_path
    from knowledge.summaries import format_architecture_md, format_context_md

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    repo = json.loads((out / "repo-map.json").read_text(encoding="utf-8"))
    catalog = json.loads((out / "symbols.json").read_text(encoding="utf-8"))
    old_shards = {item["id"]: item for item in catalog.get("shards", [])}
    changed_shards = {_shard_id(path) for path in changes}
    shard_symbols: dict[str, list[dict[str, Any]]] = {}
    for shard_id in changed_shards:
        item = old_shards.get(shard_id)
        if item and (out / item["path"]).is_file():
            shard_symbols[shard_id] = json.loads((out / item["path"]).read_text(encoding="utf-8"))["symbols"]
        else:
            shard_symbols[shard_id] = []
    files = {item["path"]: item for item in repo.get("files", [])}
    for path in changes:
        files.pop(path, None)
        shard = _shard_id(path)
        shard_symbols[shard] = [item for item in shard_symbols[shard] if item["path"] != path]
        full = root / path
        if not full.is_file():
            continue
        try:
            content = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if is_secret_file_or_content(full, content):
            continue
        suffix, subsystem = full.suffix.lower(), path.split("/", 1)[0] if "/" in path else "root"
        extracted: list[Any] = []; raw_imports: list[str] = []; unknowns: list[str] = []
        if suffix == ".py": extracted, raw_imports, _, unknowns = extract_python_file(full, path, content, subsystem)
        elif suffix in {".js", ".jsx", ".ts", ".tsx"}: extracted, raw_imports, _, unknowns = extract_javascript_file(full, path, content, subsystem)
        elif suffix in {".go", ".rs", ".java", ".c", ".cpp"}: extracted, raw_imports, _, unknowns = extract_lexical_file(full, path, content, subsystem)
        symbols = [{"name": item.name, "qualified_name": item.qualified_name, "kind": item.kind, "path": path, "line_start": item.line_start, "line_end": item.line_end, "owner": subsystem, "exported": not item.name.startswith("_"), "docstring": item.docstring} for item in extracted]
        shard_symbols[shard].extend(symbols)
        files[path] = {"path": path, "role": _role(path), "subsystem": subsystem, "language": LANGUAGES.get(suffix, ""), "hash": compute_file_hash(full), "line_count": len(content.splitlines()), "symbols": sorted(item["name"] for item in symbols), "raw_imports": sorted(set(raw_imports)), "generated": False}
    files_list = sorted(files.values(), key=lambda item: item["path"])
    paths = {item["path"] for item in files_list}
    imports: list[dict[str, Any]] = []; reverse: dict[str, list[str]] = {path: [] for path in paths}; unresolved: list[dict[str, str]] = []
    for file in files_list:
        for raw in file.get("raw_imports", []):
            target = resolve_import_to_path(raw, paths, file["path"])
            if target:
                imports.append({"source": file["path"], "target": target, "kind": "import", "confidence": "high", "evidence": [raw]}); reverse[target].append(file["path"])
            else: unresolved.append({"source": file["path"], "import": raw, "reason": "external-or-unresolved"})
    by_path = {item["path"]: item for item in files_list}
    test_links = [{"source": file["path"], "target": edge["target"], "kind": "test"} for file in files_list if file["role"] == "test" for edge in imports if edge["source"] == file["path"] and by_path[edge["target"]]["role"] == "source"]
    subsystems: dict[str, list[str]] = {}
    for file in files_list: subsystems.setdefault(file["subsystem"], []).append(file["path"])
    entry_points = [{"path": file["path"], "symbol": (file["symbols"][0] if file["symbols"] else "main"), "kind": "entry-point"} for file in files_list if Path(file["path"]).name.lower() in {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}]
    repo.update({"files": files_list, "subsystems": [{"name": key, "paths": sorted(value)} for key, value in sorted(subsystems.items())], "directories": [{"path": key, "file_count": len(value)} for key, value in sorted(subsystems.items())], "entry_points": sorted(entry_points, key=lambda item: item["path"])})
    relationships = {"schema_version": SCHEMA_VERSION, "imports": sorted(imports, key=lambda item: (item["source"], item["target"])), "calls": [], "test_links": sorted(test_links, key=lambda item: (item["source"], item["target"])), "configuration_links": [], "unresolved_imports": sorted(unresolved, key=lambda item: (item["source"], item["import"])), "reverse_imports": {key: sorted(value) for key, value in sorted(reverse.items()) if value}}
    for shard in changed_shards:
        entries = sorted(shard_symbols[shard], key=lambda item: (item["path"], item["line_start"], item["name"]))
        target = out / f"symbols/{shard}.json"
        if entries:
            encoded = serialize_json_deterministic({"schema_version": SCHEMA_VERSION, "shard": shard, "symbols": entries}); write_file_deterministic(target, encoded)
            old_shards[shard] = {"id": shard, "path": f"symbols/{shard}.json", "count": len(entries), "hash": hashlib.sha256(encoded.encode()).hexdigest()}
        elif target.exists():
            target.unlink(); old_shards.pop(shard, None)
    catalog = {"schema_version": SCHEMA_VERSION, "symbol_count": sum(item["count"] for item in old_shards.values()), "shards": [old_shards[key] for key in sorted(old_shards)]}
    artifacts = {"repo-map.json": repo, "relationships.json": relationships, "symbols.json": catalog}
    for name, data in artifacts.items(): write_file_deterministic(out / name, serialize_json_deterministic(data))
    revision, branch, dirty, untracked = get_git_info(root)
    manifest.update({"repository": {"root": ".", "revision": revision, "branch": branch, "dirty": dirty, "untracked_files": untracked}, "generation_mode": "incremental", "config_hash": _config_hash(config), "indexed_paths": sorted(paths), "file_hashes": {item["path"]: item["hash"] for item in files_list}, "artifact_hashes": {name: _digest(data) for name, data in artifacts.items()}, "changed_files": changes, "freshness_state": "fresh"})
    manifest["index_hash"] = _digest(manifest["artifact_hashes"]); manifest["inventory_hash"] = _digest(manifest["file_hashes"])
    write_file_deterministic(out / "manifest.json", serialize_json_deterministic(manifest))
    languages = sorted({item["language"] for item in files_list if item["language"]})
    write_file_deterministic(out / "context.md", format_context_md(revision, subsystems, languages, entry_points, repo.get("commands", []), unknowns=repo.get("unknowns", [])))
    write_file_deterministic(out / "architecture.md", format_architecture_md(revision, subsystems, imports, [{"path": link["source"], "targets": [link["target"]]} for link in test_links], repo.get("configurations", [])))
