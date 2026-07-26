"""Build and reconcile a bounded propagation inventory for plan-change v5."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from plan_runtime import Plan

IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".venv", "node_modules"}
TEXT_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs", ".cs", ".md", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}


def _tokens(request: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", request) if token.lower() not in {"the", "and", "with", "from", "that", "this", "plan", "change", "make", "into"}}


def _surface(path: Path, text: str, request_tokens: set[str]) -> str | None:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    suffix = path.suffix.lower()
    if "generated" in parts or ".gen." in name:
        return "generated-output"
    if "fixtures" in parts or "tests" in parts or "fixture" in name:
        return "fixture"
    if "mock" in name or "mocks" in parts:
        return "mock"
    if suffix in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"} or "config" in name:
        return "config"
    if "schema" in name or "migration" in parts or "migrations" in parts:
        return "schema"
    if suffix in {".md", ".rst"}:
        return "documentation-contract"
    if name in {"dockerfile", "compose.yml", "compose.yaml"} or ".github" in parts or "deploy" in name:
        return "deployment-hook"
    lowered = text.lower()
    if "__all__" in lowered or "export " in lowered or "from ." in lowered:
        return "re-export"
    if request_tokens and any(token in lowered for token in request_tokens):
        return "direct-caller"
    return None


def build_inventory(repo_root: Path, request: str) -> dict[str, Any]:
    """Return only auditable, likely material propagation candidates."""
    root = repo_root.resolve()
    request_tokens = _tokens(request)
    candidates: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or IGNORED_PARTS & set(path.relative_to(root).parts) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        surface = _surface(path.relative_to(root), text, request_tokens)
        if surface:
            candidates.append({"path": path.relative_to(root).as_posix(), "surface": surface})
    grouped: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["surface"]].append(candidate["path"])
    return {
        "version": 1,
        "request_sha256": __import__("hashlib").sha256(request.encode("utf-8")).hexdigest(),
        "request_tokens": sorted(request_tokens),
        "candidates": candidates,
        "counts": {surface: len(paths) for surface, paths in sorted(grouped.items())},
    }


def load_inventory(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("candidates"), list):
        raise ValueError("inventory must be a v1 inventory JSON object")
    if not all(isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("surface"), str) for item in value["candidates"]):
        raise ValueError("inventory candidates require path and surface strings")
    return value


def unresolved_candidates(plan: Plan, inventory: dict[str, Any]) -> list[str]:
    """Return inventory entries not proven by a fact plus a change or propagation disposition."""
    facts_by_path: dict[str, set[str]] = defaultdict(set)
    for fact in plan.records.get("F", ()):
        facts_by_path[fact.fields.get("path", "").replace("\\", "/")].add(fact.id)
    resolved: set[tuple[str, str]] = set()
    for propagation in plan.records.get("P", ()):
        for fact_id in re.findall(r"\bF-[1-9]\d*\b", propagation.fields.get("because", "")):
            for path, fact_ids in facts_by_path.items():
                if fact_id in fact_ids:
                    resolved.add((path, propagation.fields.get("surface", "")))
    for change in plan.records.get("CH", ()):
        fact_id = change.fields.get("evidence", "")
        for path, fact_ids in facts_by_path.items():
            if fact_id in fact_ids:
                resolved.add((path, "changed"))
    missing = []
    for item in inventory["candidates"]:
        path, surface = item["path"], item["surface"]
        if (path, surface) not in resolved and (path, "changed") not in resolved:
            missing.append(f"{surface}:{path}")
    return sorted(set(missing))
