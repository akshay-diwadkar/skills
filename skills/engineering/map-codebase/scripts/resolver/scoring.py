"""Repository-derived scoring that makes symbol evidence dominant."""

from __future__ import annotations

from collections import Counter
from typing import Any

from resolver.features import (
    LAYER_COMPONENTS,
    file_document,
    inferred_component_types,
    path_segments,
    subsystem_tokens,
    tokenize,
)
from resolver.ranking_utils import conjunctive_match, inverse_document_frequency, length_normalization
from resolver.schemas import TaskQuery
from resolver.symbol_ranker import rank_symbols

NON_OWNER_COMPONENTS = frozenset({"generated", "legacy", "migration", "documentation"})
NON_OWNER_TERMS = frozenset({"generated", "legacy", "compatibility", "compatible", "deprecated", "documentation", "migration"})
COMPONENT_MISMATCH_PENALTY = 48.0
WORKFLOW_PRIOR_CAP = 30.0
EXACT_PATH_BONUS = 1_000.0
EXACT_SYMBOL_BONUS = 600.0


def score_candidates(
    candidates: list[dict[str, Any]],
    symbols_by_path: dict[str, list[dict[str, Any]]],
    query: TaskQuery,
    *,
    exact_paths: set[str] | frozenset[str] = frozenset(),
    exact_symbol_paths: set[str] | frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Add capped semantic and symbol evidence without benchmark-specific tuning."""
    documents = {
        candidate["file"]["path"]: file_document(
            candidate["file"], symbols_by_path.get(candidate["file"]["path"], [])
        )
        for candidate in candidates
    }
    frequencies = Counter(term for terms in documents.values() for term in terms)
    average_length = sum(map(len, documents.values())) / max(len(documents), 1)
    requested_component_available = bool(
        query.requested_component_type
        and any(
            query.requested_component_type in inferred_component_types(candidate["file"])
            for candidate in candidates
        )
    )
    output: list[dict[str, Any]] = []

    for candidate in candidates:
        item = {**candidate, "evidence": dict(candidate.get("evidence", {}))}
        file = item["file"]
        path = file["path"]
        asks_for_untracked = bool(query.positive_concepts & {"untracked", "scratch", "local"})
        if file.get("tracked") is False and not asks_for_untracked:
            continue
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
        segments = path_segments(path)
        layer_match = bool(
            query.requested_layer
            and (
                query.requested_layer in segments
                or components & LAYER_COMPONENTS.get(query.requested_layer, frozenset())
            )
        )
        concept_match = bool(query.positive_concepts & tokens)
        configuration_concepts = (
            query.positive_concepts
            & tokenize(" ".join(file.get("configuration_keys", [])))
            if file.get("role") == "configuration"
            else set()
        )
        conflicts = query.excluded_concepts & tokens
        excluded_component = query.excluded_component_types & components
        excluded_role = file.get("role") in query.excluded_roles
        excluded_subsystem = bool(query.excluded_subsystem and query.excluded_subsystem in subsystems)

        semantic_score = min(16.0, lexical * 4.0)
        # Discovery's synonym evidence is repository-derived (from a filename,
        # declaration, description, or admitted source line). Preserve it in
        # semantic scoring instead of requiring the surface spelling to recur.
        semantic_score += 10.0 if any(
            family == "synonym_token" and weight > 0
            for weight, family in item["evidence"].values()
        ) else 0.0
        semantic_score += conjunctive_match((concept_match, component_match, subsystem_match))
        semantic_score += 50.0 if component_match else 0.0
        semantic_score += 18.0 if compatible_component_match else 0.0
        semantic_score += 20.0 if subsystem_match else 0.0
        semantic_score += 10.0 if layer_match else 0.0
        if configuration_concepts:
            semantic_score += min(12.0, len(configuration_concepts) * 4.0)
            item["evidence"][
                f"configuration_key: {','.join(sorted(configuration_concepts))}"
            ] = (semantic_score, "configuration_key")
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
        # A query naming a subsystem is an architectural boundary, not just a
        # soft lexical hint. Candidates outside it remain alternatives but
        # should not outrank a direct owner inside the named subsystem.
        if query.requested_subsystem and not subsystem_match and file.get("role") != "configuration":
            penalty += 28.0
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
        requested_non_owner_surface = bool(query.positive_concepts & NON_OWNER_TERMS)
        # Generated, legacy, migration, and documentation paths remain in the
        # discovery/evidence funnel, but a maintained owner cannot be inferred
        # from them unless the task explicitly asks for that surface.
        if components & NON_OWNER_COMPONENTS and not requested_non_owner_surface:
            continue
        for decoy, value in (("generated", 18.0), ("migration", 14.0), ("documentation", 12.0), ("legacy", 16.0)):
            if decoy in components and not requested_decoy:
                penalty += value
        # A named architectural component is direct owner evidence.  Generic
        # lexical overlap may still furnish alternatives, but cannot outrank
        # a candidate that actually implements the requested boundary.
        if (
            query.requested_component_type
            and requested_component_available
            and not component_match
            and not compatible_component_match
            and best_symbol < 40.0
        ):
            penalty += COMPONENT_MISMATCH_PENALTY
        # Shared utility/model surfaces frequently contain generic validation
        # vocabulary.  They are useful relationship evidence but should not
        # outrank a concrete boundary unless the task asks for shared support.
        asks_for_shared = bool(query.positive_concepts & {"shared", "common", "runtime", "utility", "utilities"})
        generic_model = components & {"model"} and not query.requested_component_type
        if not asks_for_shared and ("shared" in segments or generic_model):
            penalty += 18.0
        workflow_prior = 0.0
        if (
            query.requested_component_type is None
            and "orchestrator" in components
            and query.positive_concepts
            & {"cycle", "idempotency", "renewal", "retry", "workflow"}
            and not query.positive_concepts
            & {"delivery", "messaging", "notification", "rendered"}
        ):
            workflow_prior = min(WORKFLOW_PRIOR_CAP, best_symbol * 2.0)
        direct_score = (
            # Preserve enough bounded lexical evidence to distinguish a
            # behavior-rich owner from a large corpus of files that merely
            # repeat one domain noun.  The previous cap flattened both to the
            # same value before symbol scoring.
            min(60.0, max(0.0, float(item.get("score", 0.0))))
            + semantic_score
            + best_symbol * 1.5
            + second_symbol
            + workflow_prior
            + job_service_prior
        )
        if path in exact_paths:
            direct_score += EXACT_PATH_BONUS
            item["evidence"][f"exact_path: {path}"] = (EXACT_PATH_BONUS, "path")
        if path in exact_symbol_paths:
            direct_score += EXACT_SYMBOL_BONUS
            item["evidence"][f"exact_symbol: {path}"] = (EXACT_SYMBOL_BONUS, "identifier")
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
        # Candidate admission may use paths and fuzzy terms, but selection must
        # have a declaration, source behavior, configuration, or explicit
        # architectural boundary to stand as an owner.
        direct_families = {
            "identifier", "source_token", "description", "configuration_key",
            "configuration", "component_type", "subsystem", "layer", "relationship", "test",
            # An exact module/path match is direct repository ownership
            # evidence; generic fuzzy similarity remains outside this set.
            "path",
        }
        item["direct_evidence"] = tuple(sorted(
            key for key, (weight, family) in item["evidence"].items()
            if weight > 0 and family in direct_families
        ))
        if item["score"] > 0:
            output.append(item)
    return sorted(output, key=lambda value: (-value["score"], value["file"]["path"]))
