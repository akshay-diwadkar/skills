#!/usr/bin/env python3
"""Validate v2 knowledge artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config
from knowledge.schemas import validate_schema_json, validate_semantic_graph
from refresh_knowledge import check_freshness


def validate_knowledge(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict:
    root = Path(repo_root).resolve()
    out = Path(knowledge_dir).resolve() if knowledge_dir else root / load_config(root)["output_dir"]
    try:
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        repo = json.loads((out / "repo-map.json").read_text(encoding="utf-8"))
        rel = json.loads((out / "relationships.json").read_text(encoding="utf-8"))
        catalog = json.loads((out / "symbols.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "invalid", "errors": [str(exc)], "warnings": []}
    errors = []
    symbols = []
    for shard in catalog.get("shards", []):
        try:
            symbols.extend(json.loads((out / shard["path"]).read_text(encoding="utf-8"))["symbols"])
        except Exception as exc:
            errors.append(str(exc))
    for data, schema in [
        (manifest, "manifest.schema.json"),
        (repo, "repo-map.schema.json"),
        (rel, "relationships.schema.json"),
        (catalog, "symbols.schema.json"),
    ]:
        errors.extend(validate_schema_json(data, schema))
    errors.extend(validate_semantic_graph(root, repo, rel, symbols, manifest))
    fresh = check_freshness(root, out)
    return {
        "status": "invalid"
        if errors
        else ("valid-fresh" if fresh["status"] == "fresh" else f"valid-{fresh['status']}"),
        "freshness": fresh["status"],
        "errors": errors,
        "warnings": [],
        "files_checked": len(repo.get("files", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate_knowledge(args.repo_root, args.output)
    print(f"Validation status: {result['status']}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
