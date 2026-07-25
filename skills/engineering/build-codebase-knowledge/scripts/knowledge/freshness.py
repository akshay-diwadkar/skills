"""Inventory-aware freshness checks and safe v2 refresh."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from knowledge.config import load_config
from knowledge.discovery import discover_files, is_secret_file_or_content
from knowledge.fingerprint import compute_file_hash
from knowledge.schemas import validate_schema_json


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check_freshness(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root)
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]
    required = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json", "context.md", "architecture.md"]
    if any(not (out / name).is_file() for name in required):
        return {"status": "missing", "reason": "Required v2 artifacts are missing."}
    try:
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        catalog = json.loads((out / "symbols.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "invalid", "reason": str(exc)}
    if validate_schema_json(manifest, "manifest.schema.json") or any(
        not (out / shard["path"]).is_file() for shard in catalog.get("shards", [])
    ):
        return {"status": "invalid", "reason": "Manifest/schema or symbol shard invalid."}
    if manifest.get("ignore_hash") != _digest({key: config.get(key) for key in ("include", "exclude", "generated")}):
        return {"status": "stale", "reason": "Discovery/ignore rules changed."}
    included, _, _ = discover_files(root, config)
    current: dict[str, str] = {}
    for path in included:
        try:
            content = (root / path).read_text(encoding="utf-8", errors="ignore")
            if not is_secret_file_or_content(root / path, content):
                current[path] = compute_file_hash(root / path)
        except OSError:
            pass
    old = manifest.get("file_hashes", {})
    changed = sorted(path for path in set(old) | set(current) if old.get(path) != current.get(path))
    if changed:
        return {
            "status": "partially-stale",
            "changed_files": changed,
            "reason": f"{len(changed)} indexed inventory changes.",
        }
    return {"status": "fresh", "changed_files": []}


def refresh_knowledge(
    repo_root: Path | str, changed_files: list[str] | None = None, knowledge_dir: Path | str | None = None
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / load_config(root)["output_dir"]
    state = check_freshness(root, out)
    if state["status"] == "fresh":
        return {"mode": "none", "status": "fresh", "message": "Knowledge is already fresh."}
    from build_knowledge import build_knowledge

    result = build_knowledge(root, out)
    return {
        "mode": "full" if state["status"] in {"missing", "invalid", "stale"} else "incremental",
        "status": "fresh",
        "changed_files": changed_files or state.get("changed_files", []),
        "details": result,
    }
