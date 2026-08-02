"""Base interface and data models for language symbol and import extractors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TypedDict

COMPONENT_TYPES = (
    "policy",
    "service",
    "handler",
    "job",
    "repository",
    "adapter",
    "client",
    "model",
    "orchestrator",
    "route/controller",
    "command",
    "migration",
    "schema",
    "documentation",
    "generated",
    "legacy",
)


class SymbolEvidence(TypedDict):
    signature: str
    type_hints: list[str]
    decorators: list[str]
    interfaces: list[str]
    references: list[str]
    control_flow: list[str]
    calls: list[str]

_GENERIC_ROOTS = {
    "src",
    "app",
    "apps",
    "lib",
    "libs",
    "source",
    "packages",
    "pkg",
    "internal",
}
_PATH_COMPONENTS = {
    "policies": "policy",
    "policy": "policy",
    "services": "service",
    "service": "service",
    "handlers": "handler",
    "handler": "handler",
    "jobs": "job",
    "job": "job",
    "workers": "job",
    "repositories": "repository",
    "repository": "repository",
    "repos": "repository",
    "adapters": "adapter",
    "adapter": "adapter",
    "clients": "client",
    "client": "client",
    "models": "model",
    "model": "model",
    "orchestrators": "orchestrator",
    "orchestrator": "orchestrator",
    "routes": "route/controller",
    "route": "route/controller",
    "controllers": "route/controller",
    "controller": "route/controller",
    "commands": "command",
    "command": "command",
    "cmd": "command",
    "migrations": "migration",
    "migration": "migration",
    "schemas": "schema",
    "schema": "schema",
    "docs": "documentation",
    "doc": "documentation",
    "documentation": "documentation",
    "generated": "generated",
    "gen": "generated",
    "legacy": "legacy",
    "deprecated": "legacy",
    # Compatibility shims preserve an older integration contract.  They are
    # useful impact evidence, but should not become the primary owner of a
    # new behavior unless the task explicitly asks for compatibility work.
    "compatibility": "legacy",
}
_NAME_COMPONENTS = {
    "policy": "policy",
    "service": "service",
    "handler": "handler",
    "job": "job",
    "worker": "job",
    "repository": "repository",
    "repo": "repository",
    "adapter": "adapter",
    "client": "client",
    "model": "model",
    "orchestrator": "orchestrator",
    "route": "route/controller",
    "router": "route/controller",
    "controller": "route/controller",
    "command": "command",
    "migration": "migration",
    "schema": "schema",
}


def normalized_subsystem_path(path: str) -> str:
    """Return the meaningful directory ownership path for a repository file."""
    parts = [
        part
        for part in PurePosixPath(path.replace("\\", "/")).parts[:-1]
        if part.lower() not in _GENERIC_ROOTS
    ]
    return "/".join(parts) or "root"


def infer_component_types(
    path: str,
    *,
    name: str = "",
    decorators: list[str] | tuple[str, ...] = (),
    imports: list[str] | tuple[str, ...] = (),
    content: str = "",
    generated: bool = False,
) -> list[str]:
    """Infer ordered architectural subtypes from independent source signals."""
    found: set[str] = set()
    posix = path.replace("\\", "/")
    path_parts = [part.lower() for part in PurePosixPath(posix).parts]
    stem_tokens = re.findall(r"[a-z0-9]+", PurePosixPath(posix).stem.lower().replace("_", " "))
    name_tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", name)
    for token in [*path_parts, *stem_tokens]:
        if token in _PATH_COMPONENTS:
            found.add(_PATH_COMPONENTS[token])
    for token in name_tokens:
        mapped = _NAME_COMPONENTS.get(token.lower())
        if mapped:
            found.add(mapped)

    decorator_text = " ".join(decorators).lower()
    import_text = " ".join(imports).lower()
    lowered = content[:4096].lower()
    if re.search(r"\b(route|router|controller|requestmapping|httpget|httppost)\b", decorator_text):
        found.add("route/controller")
    if re.search(r"\b(job|scheduled|cron|task|celery)\b", decorator_text):
        found.add("job")
    if re.search(r"\b(command|click\.command|typer\.command)\b", decorator_text):
        found.add("command")
    if re.search(r"\b(repository|entityframework|sqlalchemy|django\.db)\b", import_text):
        found.add("repository")
    if generated or "generated" in path_parts or re.search(
        r"(auto[- ]generated|generated file|do not edit)", lowered
    ):
        found.add("generated")
    if "legacy" in path_parts or "deprecated" in path_parts or re.search(
        r"\b(deprecated|legacy implementation)\b", lowered
    ):
        found.add("legacy")
    if PurePosixPath(posix).suffix.lower() in {".md", ".rst", ".adoc"}:
        found.add("documentation")
    return [component for component in COMPONENT_TYPES if component in found]


@dataclass
class ExtractedSymbol:
    name: str
    qualified_name: str
    kind: str  # class, function, async-function, struct, type, export
    path: str
    line_start: int
    line_end: int
    subsystem: str
    docstring: str = ""
    component_types: list[str] = field(default_factory=list)
    signature: str = ""
    type_hints: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    control_flow: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)


@dataclass
class ExtractedFileResult:
    path: str
    subsystem: str
    role: str  # source, test, configuration
    language: str
    symbols: list[ExtractedSymbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    file_hash: str = ""
    role_summary: str = ""
    extraction_confidence: str = "high"  # high, medium, low
    unknowns: list[str] = field(default_factory=list)
