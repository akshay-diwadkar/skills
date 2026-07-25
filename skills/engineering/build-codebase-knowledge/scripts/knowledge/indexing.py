"""Shared deterministic file indexing and artifact projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from knowledge.discovery import is_binary_file, is_secret_file_or_content, matches_glob
from knowledge.extraction.configuration import extract_config_and_commands
from knowledge.extraction.javascript import extract_javascript_file
from knowledge.extraction.lexical import extract_lexical_file
from knowledge.extraction.python import extract_python_file
from knowledge.fingerprint import compute_file_hash
from knowledge.relationships import resolve_import_to_path

CONFIG_NAMES = {"pyproject.toml", "package.json", "makefile", "gnumakefile"}
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
}
ENTRY_NAMES = {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}


def shard_id(path: str) -> str:
    return (path.split("/", 1)[0] if "/" in path else "root").replace(".", "_")


def role(path: str) -> str:
    name = Path(path).name.lower()
    if (
        name in CONFIG_NAMES
        or Path(path).suffix.lower() in {".toml", ".yaml", ".yml", ".ini"}
        or path.endswith(".env.example")
    ):
        return "configuration"
    return "test" if "test" in path.lower() or name.startswith("test_") or name.endswith("_test.py") else "source"


def is_repository_wide_config(path: str) -> bool:
    return Path(path).name.lower() in CONFIG_NAMES or path == ".codebase-knowledge.toml"


@dataclass(frozen=True)
class IndexedFile:
    record: dict[str, Any]
    symbols: list[dict[str, Any]]
    configuration: dict[str, Any] | None
    commands: list[dict[str, str]]
    unknowns: list[str]


def _relative(root: Path, raw: str) -> tuple[str | None, str | None]:
    try:
        full = Path(raw).resolve() if Path(raw).is_absolute() else (root / raw).resolve()
        return full.relative_to(root.resolve()).as_posix(), None
    except ValueError:
        return None, "outside repository"


def classify_and_extract(
    root: Path, raw_path: str, config: dict[str, Any]
) -> tuple[IndexedFile | None, str, str | None]:
    """Return a complete file extraction or a stable ineligibility reason."""
    candidate = Path(raw_path) if Path(raw_path).is_absolute() else root / raw_path
    if candidate.is_symlink():
        return None, str(raw_path).replace("\\", "/"), "unsafe symlink"
    path, error = _relative(root, raw_path)
    if error or path is None:
        return None, str(raw_path), error
    full = root / path
    if not full.is_file():
        return None, path, "missing or not a regular file"
    if matches_glob(path, config["exclude"]) or (config["include"] and not matches_glob(path, config["include"])):
        return None, path, "excluded by discovery rules"
    try:
        if full.stat().st_size > config["max_file_size_bytes"]:
            return None, path, "file exceeds max_file_size_bytes"
        if is_binary_file(full):
            return None, path, "binary file"
        content = full.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return None, path, f"unreadable: {exc}"
    if is_secret_file_or_content(full, content):
        return None, path, "secret-sensitive file or content"
    subsystem, suffix = (path.split("/", 1)[0] if "/" in path else "root"), full.suffix.lower()
    extracted: list[Any] = []
    imports: list[str] = []
    unknowns: list[str] = []
    if suffix == ".py":
        extracted, imports, _, unknowns = extract_python_file(full, path, content, subsystem)
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        extracted, imports, _, unknowns = extract_javascript_file(full, path, content, subsystem)
    elif suffix in {".go", ".rs", ".java", ".c", ".cpp"}:
        extracted, imports, _, unknowns = extract_lexical_file(full, path, content, subsystem)
    symbols = [
        {
            "name": item.name,
            "qualified_name": item.qualified_name,
            "kind": item.kind,
            "path": path,
            "line_start": item.line_start,
            "line_end": item.line_end,
            "owner": subsystem,
            "exported": not item.name.startswith("_"),
            "docstring": item.docstring,
        }
        for item in extracted
    ]
    config_entry, commands = (
        extract_config_and_commands(root, path, content) if role(path) == "configuration" else (None, [])
    )
    record = {
        "path": path,
        "role": role(path),
        "subsystem": subsystem,
        "language": LANGUAGES.get(suffix, ""),
        "hash": compute_file_hash(full),
        "line_count": len(content.splitlines()),
        "symbols": sorted(item["name"] for item in symbols),
        "raw_imports": sorted(set(imports)),
        "generated": matches_glob(path, config["generated"]),
        "unknowns": sorted(unknowns),
    }
    return IndexedFile(record, symbols, config_entry, commands, unknowns), path, None


def project(
    files: list[dict[str, Any]],
    configurations: list[dict[str, Any]],
    commands: list[dict[str, str]],
    unknowns: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    files = sorted(files, key=lambda item: item["path"])
    paths = {f["path"] for f in files}
    by_path = {f["path"]: f for f in files}
    imports = []
    unresolved = []
    reverse = {path: [] for path in paths}
    for file in files:
        for raw in file["raw_imports"]:
            target = resolve_import_to_path(raw, paths, file["path"])
            if target:
                imports.append(
                    {
                        "source": file["path"],
                        "target": target,
                        "kind": "import",
                        "confidence": "high",
                        "evidence": [raw],
                    }
                )
                reverse[target].append(file["path"])
            else:
                unresolved.append({"source": file["path"], "import": raw, "reason": "external-or-unresolved"})
    tests = []
    for file in files:
        if file["role"] != "test":
            continue
        candidates = {
            edge["target"]
            for edge in imports
            if edge["source"] == file["path"] and by_path[edge["target"]]["role"] == "source"
        }
        stem = Path(file["path"]).stem.replace("test_", "").replace("_test", "")
        candidates |= {path for path, item in by_path.items() if item["role"] == "source" and Path(path).stem == stem}
        tests.extend({"source": file["path"], "target": target, "kind": "test"} for target in sorted(candidates))
    subsystems: dict[str, list[str]] = {}
    for file in files:
        subsystems.setdefault(file["subsystem"], []).append(file["path"])
    repo = {
        "schema_version": "3.0",
        "repository": {"root": ".", "languages": sorted({f["language"] for f in files if f["language"]})},
        "subsystems": [{"name": key, "paths": sorted(value)} for key, value in sorted(subsystems.items())],
        "directories": [{"path": key, "file_count": len(value)} for key, value in sorted(subsystems.items())],
        "files": files,
        "entry_points": [
            {"path": f["path"], "symbol": f["symbols"][0] if f["symbols"] else "main", "kind": "entry-point"}
            for f in files
            if Path(f["path"]).name.lower() in ENTRY_NAMES
        ],
        "commands": sorted(
            {(x["kind"], x["cmd"], x["source"]): x for x in commands}.values(),
            key=lambda x: (x["kind"], x["cmd"], x["source"]),
        ),
        "configurations": sorted(configurations, key=lambda x: x["path"]),
        "generated_paths": sorted(f["path"] for f in files if f["generated"]),
        "ignored_paths": [],
        "unknowns": sorted(set(unknowns))[:20],
    }
    relationships = {
        "schema_version": "3.0",
        "imports": sorted(imports, key=lambda x: (x["source"], x["target"])),
        "calls": [],
        "test_links": sorted(tests, key=lambda x: (x["source"], x["target"])),
        "configuration_links": [],
        "unresolved_imports": sorted(unresolved, key=lambda x: (x["source"], x["import"])),
        "reverse_imports": {path: sorted(value) for path, value in sorted(reverse.items()) if value},
    }
    return repo, relationships
