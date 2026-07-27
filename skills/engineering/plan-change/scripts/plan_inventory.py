"""Build and reconcile an anchor-first propagation inventory for plan-change v5."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from plan_runtime import Plan

IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".venv", "node_modules", ".agent"}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".kt", ".kts",
    ".go", ".java", ".rb", ".rs", ".cs",
    ".md", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
}
MANIFESTS = {
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "__init__.py",
}


def _files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not (IGNORED_PARTS & set(path.relative_to(root).parts))
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


def _definitions(path: Path, text: str) -> set[str]:
    if path.suffix != ".py":
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _request_paths(request: str) -> set[str]:
    return {
        value.strip("`'\".,:").replace("\\", "/")
        for value in re.findall(r"[A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)+", request)
    }


def _request_symbols(request: str) -> set[str]:
    ordered = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", request)
    explicit = {value for value in ordered if "_" in value or any(character.isupper() for character in value[1:])}
    joined = {
        "_".join(ordered[index : index + width]).casefold()
        for width in (2, 3)
        for index in range(len(ordered) - width + 1)
    }
    return explicit | joined


def _parse_anchor(raw: str) -> tuple[str, str]:
    path, separator, symbol = raw.partition(":")
    return path.replace("\\", "/"), symbol if separator else ""


def _python_import_targets(root: Path, path: Path, text: str) -> set[Path]:
    if path.suffix != ".py":
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    targets: set[Path] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        for module in modules:
            candidate = root / (module.replace(".", "/") + ".py")
            package = root / module.replace(".", "/") / "__init__.py"
            if candidate.is_file():
                targets.add(candidate)
            elif package.is_file():
                targets.add(package)
    return targets


def _surface(path: Path, text: str, *, seed: bool) -> str:
    parts = {part.casefold() for part in path.parts}
    name = path.name.casefold()
    if "tests" in parts or name.startswith("test_"):
        return "fixture"
    if name in MANIFESTS or path.suffix in {".toml", ".ini", ".cfg"}:
        return "config"
    if "schema" in name or path.suffix in {".json", ".yaml", ".yml"}:
        return "schema"
    if "generated" in parts or name.endswith((".generated.py", ".generated.ts")):
        return "generated-output"
    if "generate" in name or "generator" in name:
        return "generator"
    if path.suffix in {".md", ".rst"}:
        return "documentation-contract"
    if ".github" in parts or "deploy" in name:
        return "deployment-hook"
    if path.suffix.lower() in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"} and re.search(
        r"\bexport\s+(?:\{[^}]+\}|\*)\s+from\s+['\"]", text, re.DOTALL
    ):
        return "re-export"
    return "direct-caller" if seed else "transitive-consumer"


def build_inventory(repo_root: Path, request: str, anchors: list[str] | None = None) -> dict[str, Any]:
    """Discover bounded candidates outward from verified paths and symbol definitions."""
    root = repo_root.resolve()
    files = _files(root)
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}
    definitions = {path: _definitions(path, text) for path, text in texts.items()}
    seeds: dict[Path, set[str]] = defaultdict(set)
    for raw in anchors or []:
        relative, symbol = _parse_anchor(raw)
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"anchor escapes repository: {raw}") from exc
        if not path.is_file() or path not in texts:
            raise ValueError(f"anchor path is not an indexed text file: {raw}")
        if symbol and symbol not in definitions[path] and not re.search(rf"\b{re.escape(symbol)}\b", texts[path]):
            raise ValueError(f"anchor symbol is absent: {raw}")
        seeds[path].add(symbol or path.stem)
    for relative in _request_paths(request):
        path = (root / relative).resolve()
        if path in texts:
            seeds[path].add(path.stem)
    for symbol in _request_symbols(request):
        owners = [path for path, names in definitions.items() if symbol in names]
        if len(owners) == 1:
            seeds[owners[0]].add(symbol)
    if not seeds:
        raise ValueError("inventory requires at least one grounded path or uniquely defined symbol; pass --anchor PATH[:SYMBOL]")

    provenance: dict[Path, set[str]] = defaultdict(set)
    distance: dict[Path, int] = {}
    queue: deque[Path] = deque()
    for path, symbols in seeds.items():
        distance[path] = 0
        queue.append(path)
        provenance[path].update(f"anchor:{symbol}" for symbol in symbols)

    while queue:
        current = queue.popleft()
        if distance[current] >= 2:
            continue
        current_symbols = definitions[current] | seeds.get(current, set())
        related: dict[Path, str] = {}
        for imported in _python_import_targets(root, current, texts[current]):
            related[imported] = f"import:{current.relative_to(root).as_posix()}"
        module_name = current.stem
        for candidate, text in texts.items():
            if candidate == current:
                continue
            if any(re.search(rf"\b{re.escape(symbol)}\b", text) for symbol in current_symbols if symbol):
                related[candidate] = f"reference:{module_name}"
            elif re.search(rf"\b(?:from|import)\s+[\w.]*{re.escape(module_name)}\b", text):
                related[candidate] = f"importer:{module_name}"
        for parent in (current.parent, *current.parents):
            if parent == root.parent:
                break
            for manifest in MANIFESTS:
                candidate = parent / manifest
                if candidate in texts:
                    related[candidate] = f"owner:{current.relative_to(root).as_posix()}"
            if parent == root:
                break
        for candidate, reason in related.items():
            provenance[candidate].add(reason)
            if candidate not in distance:
                distance[candidate] = distance[current] + 1
                queue.append(candidate)

    candidates: list[dict[str, Any]] = [
        {
            "path": path.relative_to(root).as_posix(),
            "surface": _surface(path.relative_to(root), texts[path], seed=path in seeds),
            "anchor": ",".join(sorted(seeds.get(path, definitions[path]))) or path.stem,
            "provenance": sorted(provenance[path]),
        }
        for path in sorted(distance)
    ]
    grouped: dict[str, list[str]] = defaultdict(list)
    for inventory_candidate in candidates:
        grouped[inventory_candidate["surface"]].append(inventory_candidate["path"])
    return {
        "version": 2,
        "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
        "anchors": sorted(
            f"{path.relative_to(root).as_posix()}:{symbol}"
            for path, symbols in seeds.items()
            for symbol in symbols
        ),
        "candidates": candidates,
        "counts": {surface: len(paths) for surface, paths in sorted(grouped.items())},
    }


def load_inventory(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != 2 or not isinstance(value.get("candidates"), list):
        raise ValueError("inventory must be a v2 inventory JSON object")
    required = {"path", "surface", "anchor", "provenance"}
    if not all(
        isinstance(item, dict)
        and required <= set(item)
        and all(isinstance(item[field], str) for field in ("path", "surface", "anchor"))
        and isinstance(item["provenance"], list)
        and all(isinstance(reason, str) for reason in item["provenance"])
        for item in value["candidates"]
    ):
        raise ValueError("inventory candidates require path, surface, anchor, and provenance")
    return value


def unresolved_candidates(plan: Plan, inventory: dict[str, Any]) -> list[str]:
    """Return relevant inventory entries not proven by evidence and disposition."""
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
        for fact_id in re.findall(r"\bF-[1-9]\d*\b", change.fields.get("evidence", "")):
            for path, fact_ids in facts_by_path.items():
                if fact_id in fact_ids:
                    resolved.add((path, "changed"))
    missing = [
        f"{item['surface']}:{item['path']}"
        for item in inventory["candidates"]
        if (item["path"], item["surface"]) not in resolved and (item["path"], "changed") not in resolved
    ]
    return sorted(set(missing))
