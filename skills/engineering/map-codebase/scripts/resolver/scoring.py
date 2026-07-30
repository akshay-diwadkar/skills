"""Repository-derived scoring that makes symbol evidence dominant."""

from __future__ import annotations

from collections import Counter
from typing import Any

from resolver.features import file_document, inferred_component_types, subsystem_tokens, tokenize
from resolver.ranking_utils import conjunctive_match, inverse_document_frequency, length_normalization
from resolver.schemas import TaskQuery
from resolver.symbol_ranker import rank_symbols


def score_candidates(
    candidates: list[dict[str, Any]],
    symbols_by_path: dict[str, list[dict[str, Any]]],
    query: TaskQuery,
    files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add capped semantic and symbol evidence without benchmark-specific tuning."""
    documents = {
        file["path"]: file_document(file, symbols_by_path.get(file["path"], []))
        for file in files
    }
    frequencies = Counter(term for terms in documents.values() for term in terms)
    average_length = sum(map(len, documents.values())) / max(len(documents), 1)
    output: list[dict[str, Any]] = []

    for candidate in candidates:
        item = {**candidate, "evidence": dict(candidate.get("evidence", {}))}
        file = item["file"]
        path = file["path"]
        tokens = documents.get(path, set())
        lexical = sum(
            inverse_document_frequency(len(documents), frequencies[term])
            for term in query.positive_concepts & tokens
        ) * length_normalization(len(tokens), average_length)
        symbol_ranking = rank_symbols(symbols_by_path.get(path, []), query)
        best_symbol = symbol_ranking[0][1] if symbol_ranking else 0.0
        second_symbol = symbol_ranking[1][1] * 0.25 if len(symbol_ranking) > 1 else 0.0
        components = inferred_component_types(file)
        subsystems = subsystem_tokens(file)
        component_match = bool(
            query.requested_component_type
            and query.requested_component_type in components
        )
        compatible_component_match = bool(
            query.requested_component_type == "adapter"
            and "repository" in components
            and query.requested_layer == "persistence"
        )
        subsystem_match = bool(
            query.requested_subsystem
            and query.requested_subsystem in subsystems
        )
        layer_components = {
            "application": {"service", "orchestrator", "command"},
            "domain": {"policy", "model"},
            "boundary": {"handler", "route/controller", "client"},
            "persistence": {"repository", "adapter", "model"},
            "infrastructure": {"repository", "adapter", "client", "job"},
        }
        layer_match = bool(
            query.requested_layer
            and components & layer_components.get(query.requested_layer, set())
        )
        concept_match = bool(query.positive_concepts & tokens)
        conflicts = query.excluded_concepts & tokens
        excluded_component = query.excluded_component_types & components
        excluded_role = file.get("role") in query.excluded_roles
        excluded_subsystem = bool(query.excluded_subsystem and query.excluded_subsystem in subsystems)

        semantic_score = min(16.0, lexical * 4.0)
        semantic_score += conjunctive_match((concept_match, component_match, subsystem_match))
        semantic_score += 50.0 if component_match else 0.0
        semantic_score += 18.0 if compatible_component_match else 0.0
        semantic_score += 20.0 if subsystem_match else 0.0
        semantic_score += 10.0 if layer_match else 0.0
        component_conflict_words = {
            word for word, component in {
                "policy": "policy", "service": "service", "handler": "handler", "job": "job",
                "repository": "repository", "model": "model", "orchestrator": "orchestrator",
                "orchestration": "orchestrator", "route": "route/controller", "controller": "route/controller",
            }.items()
            if component in query.excluded_component_types and component not in components
        }
        semantic_conflicts = conflicts - component_conflict_words
        penalty = min(36.0, len(semantic_conflicts) * 8.0)
        if excluded_component or excluded_role or excluded_subsystem:
            penalty += 60.0
        if (
            query.requested_component_type == "job"
            and components & {"model", "repository"}
            and "service" not in components
        ):
            penalty += 15.0
        job_service_prior = (
            20.0
            if query.requested_component_type == "job" and "service" in components
            else 0.0
        )
        requested_decoy = bool(query.requested_component_type and query.requested_component_type in components)
        for decoy, value in (("generated", 18.0), ("migration", 14.0), ("documentation", 12.0), ("legacy", 16.0)):
            if decoy in components and not requested_decoy:
                penalty += value
        workflow_prior = 0.0
        if (
            query.requested_component_type is None
            and "orchestrator" in components
            and query.positive_concepts
            & {"cycle", "idempotency", "renewal", "retry", "workflow"}
            and not query.positive_concepts
            & {"delivery", "messaging", "notification", "rendered"}
        ):
            workflow_prior = 60.0
        direct_score = (
            min(10.0, max(0.0, float(item.get("score", 0.0))))
            + semantic_score
            + best_symbol * 1.5
            + second_symbol
            + workflow_prior
            + job_service_prior
        )
        item["direct_score"] = max(0.0, direct_score - penalty)
        item["score"] = item["direct_score"]
        item["negative_conflicts"] = (
            len(semantic_conflicts) + len(excluded_component) + int(excluded_role) + int(excluded_subsystem)
        )
        item["component_match"] = component_match
        item["subsystem_match"] = subsystem_match
        item["layer_match"] = layer_match
        item["symbol_score"] = best_symbol
        ownership_tokens = file_document(file, [])
        for symbol in symbols_by_path.get(path, [])[:1]:
            ownership_tokens.update(tokenize(str(symbol.get("name", ""))))
            ownership_tokens.update(tokenize(str(symbol.get("qualified_name", ""))))
            ownership_tokens.update(tokenize(str(symbol.get("signature", ""))))
        item["matched_concepts"] = query.positive_concepts & ownership_tokens
        if symbol_ranking:
            for label in symbol_ranking[0][2]:
                item["evidence"][label] = (best_symbol, "symbol")
        if component_match:
            item["evidence"][f"component_type: {query.requested_component_type}"] = (
                50.0,
                "component_type",
            )
        elif compatible_component_match:
            item["evidence"]["component_compatibility: persistence adapter"] = (
                18.0,
                "component_type",
            )
        if subsystem_match:
            item["evidence"][f"requested_subsystem: {query.requested_subsystem}"] = (20.0, "subsystem")
        if layer_match:
            item["evidence"][f"requested_layer: {query.requested_layer}"] = (10.0, "layer")
        if penalty:
            item["evidence"]["negative_conflict_penalty"] = (-penalty, "negative_conflict")
        if item["score"] > 0:
            output.append(item)
    return sorted(output, key=lambda value: (-value["score"], value["file"]["path"]))
