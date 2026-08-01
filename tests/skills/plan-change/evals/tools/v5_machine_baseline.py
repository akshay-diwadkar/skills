"""Evaluation-only model of the removed v5 preparation phase.

This module deliberately retains exhaustive traversal for historical timing
comparison. Runtime code and normal plan-change tests must never import it.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".venv", "node_modules", ".agent"}
TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".kt",
    ".kts",
    ".go",
    ".java",
    ".rb",
    ".rs",
    ".cs",
    ".md",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}
MANIFESTS = {
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "__init__.py",
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
    return "direct-caller" if seed else "transitive-consumer"


def build_inventory(repo_root: Path, request: str, anchor: str) -> dict[str, Any]:
    """Run the removed v5 exhaustive anchor-first inventory algorithm."""
    root = repo_root.resolve()
    files = _files(root)
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}
    definitions = {path: _definitions(path, text) for path, text in texts.items()}
    raw_path, _, symbol = anchor.partition(":")
    seed = (root / raw_path).resolve()
    if seed not in texts or (symbol and symbol not in definitions[seed] and symbol not in texts[seed]):
        raise ValueError(f"invalid v5 benchmark anchor: {anchor}")
    distance = {seed: 0}
    provenance: dict[Path, set[str]] = defaultdict(set)
    provenance[seed].add(f"anchor:{symbol or seed.stem}")
    queue: deque[Path] = deque([seed])
    while queue:
        current = queue.popleft()
        if distance[current] >= 2:
            continue
        current_symbols = definitions[current] | {symbol or current.stem}
        related: dict[Path, str] = {
            imported: f"import:{current.relative_to(root).as_posix()}"
            for imported in _python_import_targets(root, current, texts[current])
        }
        for candidate, text in texts.items():
            if candidate != current and any(
                re.search(rf"\b{re.escape(name)}\b", text) for name in current_symbols if name
            ):
                related[candidate] = f"reference:{current.stem}"
        for candidate, reason in related.items():
            provenance[candidate].add(reason)
            if candidate not in distance:
                distance[candidate] = distance[current] + 1
                queue.append(candidate)
    candidates = [
        {
            "path": path.relative_to(root).as_posix(),
            "surface": _surface(path.relative_to(root), texts[path], seed=path == seed),
            "anchor": symbol or path.stem,
            "provenance": sorted(provenance[path]),
        }
        for path in sorted(distance)
    ]
    return {
        "version": 2,
        "request_sha256": hashlib.sha256(request.encode()).hexdigest(),
        "anchors": [anchor],
        "candidates": candidates,
    }


def prepare(
    repo_root: Path,
    request_file: Path,
    run_dir: Path,
    scaffold: str,
    snapshot,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute the removed v5 baseline/snapshot/inventory/scaffold phase."""
    request = request_file.read_text(encoding="utf-8")
    run_dir.mkdir(parents=True, exist_ok=False)
    baseline = snapshot(repo_root)
    inventory = build_inventory(repo_root, request, "src/target.py:target")
    (run_dir / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    (run_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (run_dir / "draft.md").write_text(scaffold, encoding="utf-8")
    return baseline, inventory
