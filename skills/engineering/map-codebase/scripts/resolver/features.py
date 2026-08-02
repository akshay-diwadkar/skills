"""Resolver feature extraction independent of benchmark fixtures."""

from __future__ import annotations

import re
from typing import Any

from resolver.query_parser import COMPONENT_ALIASES, GENERIC_ROOTS
from resolver.schemas import TaskQuery


LAYER_COMPONENTS: dict[str, frozenset[str]] = {
    "application": frozenset({"service", "orchestrator", "command"}),
    "domain": frozenset({"policy", "model"}),
    "boundary": frozenset({"handler", "route/controller", "client"}),
    "persistence": frozenset({"repository", "adapter", "model"}),
    "infrastructure": frozenset({"repository", "adapter", "client", "job"}),
}


def path_segments(path: str) -> set[str]:
    """Return normalized path segments on either supported host path style."""
    return {segment.casefold() for segment in path.replace("\\", "/").split("/") if segment}


def tokenize(value: str) -> set[str]:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[_/\\.-]+", " ", normalized)
    result: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", normalized):
        token = raw.casefold()
        result.add(token)
        if len(token) > 4 and token.endswith("ies"):
            result.add(token[:-3] + "y")
        elif len(token) > 4 and token.endswith("ed"):
            result.update((token[:-1], token[:-2]))
        elif len(token) > 4 and token.endswith("ing"):
            result.update((token[:-3], token[:-3] + "e"))
        elif len(token) > 4 and token.endswith("es"):
            result.update((token[:-1], token[:-2]))
        elif len(token) > 4 and token.endswith("s"):
            result.add(token[:-1])
    return result


def inferred_component_types(file: dict[str, Any]) -> set[str]:
    explicit = set(file.get("component_types", []))
    path_tokens = tokenize(file.get("path", ""))
    explicit.update(COMPONENT_ALIASES[token] for token in path_tokens if token in COMPONENT_ALIASES)
    if file.get("generated"):
        explicit.add("generated")
    return explicit


def subsystem_tokens(file: dict[str, Any]) -> set[str]:
    explicit = file.get("subsystem_path", file.get("normalized_subsystem_path", []))
    if isinstance(explicit, str):
        explicit = explicit.split("/")
    values = {str(value).casefold() for value in explicit if str(value)}
    normalized_path = str(file.get("path", "")).replace("\\", "/")
    parts = path_segments(normalized_path)
    parts.discard(normalized_path.rsplit("/", 1)[-1].casefold())
    tokens = (values | parts) - GENERIC_ROOTS
    tokens.update(token[:-1] for token in tuple(tokens) if len(token) > 4 and token.endswith("s"))
    return tokens


def file_document(file: dict[str, Any], symbols: list[dict[str, Any]]) -> set[str]:
    fields = [
        file.get("path", ""),
        file.get("subsystem", ""),
        " ".join(file.get("configuration_keys", [])),
    ]
    for symbol in symbols:
        fields.extend([
            symbol.get("name", ""),
            symbol.get("qualified_name", ""),
            symbol.get("signature", ""),
            symbol.get("docstring", ""),
            " ".join(symbol.get("decorators", [])),
            " ".join(symbol.get("interfaces", [])),
            " ".join(symbol.get("references", [])),
            " ".join(symbol.get("control_flow", [])),
        ])
    return tokenize(" ".join(str(field) for field in fields))


def structured_candidate_paths(files: list[dict[str, Any]], query: TaskQuery) -> set[str]:
    """Return bounded-dimension candidates before symbol shards are loaded."""
    result: set[str] = set()
    for file in files:
        components = inferred_component_types(file)
        subsystems = subsystem_tokens(file)
        path_terms = tokenize(file.get("path", ""))
        component_match = bool(
            query.requested_component_type
            and query.requested_component_type in components
        )
        layer_match = bool(
            query.requested_layer
            and components & LAYER_COMPONENTS.get(query.requested_layer, frozenset())
        )
        subsystem_match = bool(
            query.requested_subsystem
            and query.requested_subsystem in subsystems
        )
        concept_match = bool(query.positive_concepts & path_terms)
        configuration_match = bool(
            file.get("role") == "configuration"
            and query.positive_concepts
            & tokenize(" ".join(file.get("configuration_keys", [])))
        )
        if configuration_match:
            result.add(file["path"])
        if concept_match and (
            component_match
            or layer_match
            or subsystem_match and (query.requested_component_type is not None or query.requested_layer is not None)
        ):
            result.add(file["path"])
    return result
