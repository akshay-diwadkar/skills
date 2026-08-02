"""Shared deterministic file indexing and artifact projections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from knowledge.discovery import is_binary_file, is_secret_file_or_content, matches_glob
from knowledge.extraction.base import infer_component_types, normalized_subsystem_path
from knowledge.extraction.configuration import extract_config_and_commands
from knowledge.extraction.csharp import extract_csharp_file
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
    ".cs": "C#",
}
ENTRY_NAMES = {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}


# ---------------------------------------------------------------------------
# Extractor registry: suffix -> extraction function
# Each extractor has signature:
#   (full_path: Path, rel_str: str, content: str, subsystem: str)
#     -> tuple[list[ExtractedSymbol], list[str], str, list[str]]
# ---------------------------------------------------------------------------
_EXTRACTORS: dict[str, Any] = {}


def register_extractor(suffixes: list[str], func: Any) -> None:
    """Register an extraction function for one or more file suffixes."""
    for suffix in suffixes:
        _EXTRACTORS[suffix] = func


def _get_extractor(suffix: str) -> Any | None:
    """Look up the registered extractor for a file suffix."""
    return _EXTRACTORS.get(suffix)


# Register built-in extractors
register_extractor([".py"], extract_python_file)
register_extractor([".js", ".jsx", ".ts", ".tsx"], extract_javascript_file)
register_extractor([".go", ".rs", ".java", ".c", ".cpp"], extract_lexical_file)

register_extractor([".cs"], extract_csharp_file)


def shard_id(path: str) -> str:
    return (path.split("/", 1)[0] if "/" in path else "root").replace(".", "_")


def role(path: str) -> str:
    name = Path(path).name.lower()
    parts = tuple(part.lower() for part in Path(path).parts)
    if (
        name in CONFIG_NAMES
        or name.startswith("tsconfig") and name.endswith(".json")
        or Path(path).suffix.lower() in {".toml", ".yaml", ".yml", ".ini", ".cfg"}
        or parts[:1] in {
            ("config",),
            ("configuration",),
            ("schemas",),
            ("settings",),
        }
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
    candidate = Path(raw)
    if not candidate.is_absolute():
        normalized = raw.replace("\\", "/").strip("/")
        parts = tuple(part for part in normalized.split("/") if part and part != ".")
        if ".." not in parts:
            # Discovery supplies repository-relative, non-symlink inventory
            # paths. Keeping those paths lexical avoids a Windows realpath
            # call for every file in a large repository.
            return "/".join(parts), None
    try:
        full = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
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
    extractor = _get_extractor(suffix)
    if extractor is not None:
        extracted, imports, _, unknowns = extractor(full, path, content, subsystem)
    generated = matches_glob(path, config["generated"])
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
            "component_types": infer_component_types(
                path,
                name=item.name,
                decorators=item.decorators,
                imports=imports,
                content=content,
                generated=generated,
            ),
            "signature": item.signature,
            "type_hints": sorted(set(item.type_hints)),
            "decorators": sorted(set(item.decorators)),
            "interfaces": sorted(set(item.interfaces)),
            "references": sorted(set(item.references)),
            "control_flow": sorted(set(item.control_flow)),
            "calls": sorted(set(item.calls)),
        }
        for item in extracted
    ]
    config_entry, commands = (
        extract_config_and_commands(root, path, content) if role(path) == "configuration" else (None, [])
    )
    generated_source_match = re.search(r"(?im)^\s*(?:#|//|/\*|\*)\s*Generated from\s+([^\s.]+(?:/[^\s.]+)*\.[A-Za-z0-9]+)", content)
    record = {
        "path": path,
        "role": role(path),
        "subsystem": subsystem,
        "normalized_subsystem_path": normalized_subsystem_path(path),
        "component_types": infer_component_types(
            path,
            name=" ".join(item.name for item in extracted),
            decorators=tuple(value for item in extracted for value in item.decorators),
            imports=imports,
            content=content,
            generated=generated,
        ),
        "language": LANGUAGES.get(suffix, ""),
        "hash": compute_file_hash(full),
        "line_count": len(content.splitlines()),
        "symbols": sorted(item["name"] for item in symbols),
        "raw_imports": sorted(set(imports)),
        "generated": generated,
        "generated_source": generated_source_match.group(1).replace("\\", "/") if generated_source_match else None,
        "calls": sorted({call for item in extracted for call in item.calls}),
        "unknowns": sorted(unknowns),
    }
    return IndexedFile(record, symbols, config_entry, commands, unknowns), path, None


def project(
    files: list[dict[str, Any]],
    configurations: list[dict[str, Any]],
    commands: list[dict[str, str]],
    unknowns: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    files = sorted(files, key=lambda item: item["path"])
    paths = {f["path"] for f in files}
    by_path = {f["path"]: f for f in files}
    suffix_index_values: dict[str, list[str]] = {}
    for path in sorted(paths):
        parts = path.split("/")
        for index in range(len(parts)):
            suffix_index_values.setdefault("/".join(parts[index:]), []).append(path)
    suffix_index = {
        suffix: tuple(values) for suffix, values in suffix_index_values.items()
    }
    imports: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    reverse: dict[str, list[str]] = {path: [] for path in paths}
    for file in files:
        for raw in file["raw_imports"]:
            target = resolve_import_to_path(raw, paths, file["path"], suffix_index)
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
    tests: list[dict[str, str]] = []
    imports_by_source: dict[str, set[str]] = {}
    for edge in imports:
        imports_by_source.setdefault(edge["source"], set()).add(edge["target"])
    sources_by_stem: dict[str, set[str]] = {}
    for path, item in by_path.items():
        if item["role"] == "source":
            sources_by_stem.setdefault(Path(path).stem, set()).add(path)
    generated_links = [
        {"source": file["path"], "target": file["generated_source"], "kind": "generated-from", "confidence": "high"}
        for file in files
        if file.get("generated_source") in paths
    ]
    for file in files:
        if file["role"] != "test":
            continue
        candidates = {
            target for target in imports_by_source.get(file["path"], set())
            if by_path[target]["role"] == "source"
        }
        stem = Path(file["path"]).stem.replace("test_", "").replace("_test", "")
        candidates |= sources_by_stem.get(stem, set())
        tests.extend({"source": file["path"], "target": target, "kind": "test"} for target in sorted(candidates))
    subsystems: dict[str, list[str]] = {}
    for file in files:
        subsystems.setdefault(file["subsystem"], []).append(file["path"])
    repo = {
        "schema_version": "6.0",
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
        "unknowns": sorted({f"{file['path']}: {item}" for file in files for item in file.get("unknowns", [])})[:20],
    }
    symbols_by_name: dict[str, set[str]] = {}
    for file in files:
        for symbol in file["symbols"]:
            symbols_by_name.setdefault(symbol.lower(), set()).add(file["path"])
    calls = []
    for file in files:
        for called in file.get("calls", []):
            called_name = called.rsplit(".", 1)[-1].lower()
            targets = symbols_by_name.get(called_name, set())
            if len(targets) == 1:
                target = next(iter(targets))
                if target != file["path"]:
                    calls.append(
                        {
                            "source": file["path"],
                            "target": target,
                            "kind": "call",
                            "confidence": "medium",
                            "evidence": [called],
                        }
                    )
    relationships = {
        "schema_version": "6.0",
        "imports": sorted(imports, key=lambda x: (x["source"], x["target"])),
        "calls": sorted(calls, key=lambda x: (x["source"], x["target"], x["evidence"][0])),
        "test_links": sorted(tests, key=lambda x: (x["source"], x["target"])),
        "configuration_links": [],
        "generated_links": sorted(generated_links, key=lambda item: (item["source"], item["target"])),
        "unresolved_imports": sorted(unresolved, key=lambda x: (x["source"], x["import"])),
        "reverse_imports": {path: sorted(value) for path, value in sorted(reverse.items()) if value},
    }
    return repo, relationships
