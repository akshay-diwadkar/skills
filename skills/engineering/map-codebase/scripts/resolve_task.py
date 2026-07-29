#!/usr/bin/env python3
"""Bounded, phase-scoped repository task resolver."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from tokenizer import count_tokens

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config, resolve_knowledge_directory
from knowledge.discovery import knowledge_output_prefix
from knowledge.indexing import shard_id
from knowledge.schemas import validate_schema_json
from refresh_knowledge import check_freshness

STOPWORDS = {
    "add",
    "change",
    "fix",
    "implement",
    "make",
    "update",
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "that",
    "this",
    "code",
    "file",
    "error",
    "issue",
    "a",
    "an",
    "are",
    "is",
    "its",
    "own",
    "owned",
    "owner",
    "owns",
    "determine",
    "identify",
    "locate",
    "implementation",
}
CONFIG_NAMES = {"pyproject.toml", "package.json", "makefile", "gnumakefile", "tsconfig.json"}
CONFIG_EXTENSIONS = {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}
CONFIG_PHRASES = {
    "ruff line length", "mypy strict", "pytest addopts", "package json script", "workflow trigger",
    "github actions matrix", "tool ruff", "tool pytest ini options", "eslint", "prettier", "tsconfig",
    "package test script", "package lint script", "package build script", "npm test flag",
    "compiler options", "typescript compiler strictness", "python linter configuration",
}
STRONG_CONFIG_TOKENS = {
    "ruff", "mypy", "eslint", "prettier", "tsconfig", "addopts", "ini_options", "workflow",
    "pyproject", "compileroptions",
}
PROTECTED_COMPOUND_TERMS = {
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "GitHub": "github",
    "GitLab": "gitlab",
    "PostgreSQL": "postgresql",
    "OAuth": "oauth",
    "GraphQL": "graphql",
    "WebSocket": "websocket",
    "sign in": "signin",
}
PROTECTED_COMPOUND_PATTERN = re.compile(
    r"\b(?:" + "|".join(sorted(map(re.escape, PROTECTED_COMPOUND_TERMS), key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)
WEAK_FILENAME_TERMS = frozenset({
    "component", "config", "configuration", "service", "settings", "script", "test", "tests",
})
TEST_PHRASES = {"failing assertion", "change the fixture", "update the regression test", "fix test", "assertion", "fixture", "rename test", "expected output"}
IMPLEMENTATION_WORDS = {"implement", "add", "fix", "support", "prevent", "handle", "refactor", "caller", "behavior"}
SYNONYM_GROUPS = (
    frozenset({
        "retry",
        "retries",
        "backoff",
        "attempt",
        "attempts",
        "repeat",
        "repeated",
        "repeating",
    }),
    frozenset({
        "auth",
        "authentication",
        "authenticate",
        "authenticated",
        "unauthenticated",
        "login",
        "signin",
        "credential",
        "credentials",
    }),
    frozenset({"config", "configuration", "settings", "options"}),
    frozenset({"error", "errors", "failure", "failures", "exception", "exceptions"}),
    frozenset({"cache", "caching", "memoization", "memoize"}),
    frozenset({"search", "searching", "find", "lookup", "fetch", "retrieve", "retrieval"}),
    frozenset({"store", "storage", "persist", "persistence", "adapter"}),
    frozenset({"permission", "permissions", "access", "authorization", "authorize"}),
    frozenset({"throttle", "throttling", "ratelimit", "ratelimits"}),
    frozenset({"delete", "deletion", "remove", "removal"}),
    frozenset({"serialize", "serialization", "encode", "encoding"}),
    frozenset({"parse", "parsing", "decode", "decoding"}),
    frozenset({"timeout", "timeouts", "deadline", "deadlines"}),
    frozenset({"queue", "queues", "worker", "workers", "job", "jobs"}),
    frozenset({"validate", "validation", "verify", "verification", "check", "checks"}),
    frozenset({"create", "creation", "add", "addition", "insert"}),
    frozenset({"update", "revision", "modify", "modification"}),
    frozenset({"gradual", "progressive", "percentage", "rollout"}),
    frozenset({"cap", "ceiling", "maximum", "limit"}),
    frozenset({"schedule", "scheduled", "scheduling"}),
    frozenset({"activate", "activated", "activation"}),
    frozenset({
        "deduplicate",
        "duplicate",
        "duplicates",
        "idempotency",
        "idempotent",
        "once",
        "replay",
        "replayed",
        "seen",
        "set",
        "twice",
        "unique",
    }),
)
TOKEN_SYNONYMS = {
    token: group - {token}
    for group in SYNONYM_GROUPS
    for token in group
}
SecondaryRole = Literal["test", "configuration"]
PrimaryRole = Literal["source", "test", "configuration"]
INTENT_RULES: list[tuple[re.Pattern[str], PrimaryRole, int]] = [
    (re.compile(r"^(?:ci|build|chore\(ci\)|fix\(ci\)):"), "configuration", 260),
    (re.compile(r"^(?:test|tests)(?:\([^)]*\))?:"), "test", 260),
    (
        re.compile(
            r"(?=.*\b(?:implement|support|expose)\b)"
            r"(?=.*\b(?:tests?|assertion|fixture|expected|configuration|config|settings|options|"
            r"ruff|mypy|eslint|prettier|tsconfig|workflow|compiler|linter|addopts|matrix)\b)"
        ),
        "source",
        220,
    ),
    (
        re.compile(
            r"\b(?:failing (?:\w+ )*test|failing assertion|fix (?:the )?assertion|change (?:the )?fixture|"
            r"update (?:the )?(?:regression )?tests?|rename (?:the )?(?:regression )?tests?|"
            r"correct (?:the )?expected|expected (?:\w+ )*output|stabilize (?:the )?(?:\w+ )*fixture)\b"
        ),
        "test",
        190,
    ),
    (
        re.compile(
            r"\b(?:(?:unit|integration|contract)[- ]level verification|"
            r"verification\b.{0,40}\b(?:behavior|contract|inventory|modules?))\b"
        ),
        "test",
        185,
    ),
    (re.compile(r"\b(?:add|create|write)\b.{0,40}\b(?:regression )?tests?\b"), "test", 180),
    (
        re.compile(
            r"\b(?:ruff|mypy|eslint|prettier|tsconfig|typescript configuration|workflow trigger|"
            r"github actions|addopts|ini options|package script|npm test flag|compiler options|"
            r"package (?:test|lint|build) (?:script|command)|javascript lint script|"
            r"typescript (?:compiler strictness|compilation)|linter configuration|line[- ]?length|"
            r"requests per minute|throttling settings|yaml workflow settings|permissions matrix)\b"
        ),
        "configuration",
        170,
    ),
    (
        re.compile(r"\b(?:assertion|fixture|regression test|tests?|expected output)\b"),
        "test",
        130,
    ),
    (
        re.compile(
            r"\b(?:implement|add|fix|support|prevent|handle|refactor|caller|behavior|repair|"
            r"harden|improve|strengthen|tighten|restore|rebuild|stabilize|correct|modify|update)\b"
        ),
        "source",
        120,
    ),
    (
        re.compile(r"\b(?:configuration|config|compiler|linter|workflow|matrix)\b"),
        "configuration",
        90,
    ),
]
ROLE_ORDER: tuple[PrimaryRole, ...] = ("source", "test", "configuration")


@dataclass(frozen=True)
class TaskIntent:
    """Deterministic primary ownership and explicitly requested constraints."""

    primary_role: PrimaryRole
    secondary_roles: tuple[SecondaryRole, ...]
    reasons: tuple[str, ...]


def _literal_split(value: str) -> set[str]:
    protected = PROTECTED_COMPOUND_PATTERN.sub(
        lambda match: PROTECTED_COMPOUND_TERMS.get(
            match.group(0),
            next(
                canonical
                for term, canonical in PROTECTED_COMPOUND_TERMS.items()
                if term.lower() == match.group(0).lower()
            ),
        ),
        value,
    )
    words = (
        re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", protected)
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
        .split()
    )
    return {word.lower() for word in words if len(word) > 1 and word.lower() not in STOPWORDS}


def _stems(token: str) -> set[str]:
    """Return conservative deterministic stems without external language tooling."""
    stems = {token}
    if len(token) > 4 and token.endswith("ies"):
        stems.add(token[:-3] + "y")
    if len(token) > 5 and token.endswith("ing"):
        base = token[:-3]
        stems.add(base)
        if len(base) > 2 and base[-1] == base[-2]:
            stems.add(base[:-1])
    if len(token) > 4 and token.endswith("ed"):
        base = token[:-2]
        stems.add(base)
        stems.add(base + "e")
        if len(base) > 2 and base[-1] == base[-2]:
            stems.add(base[:-1])
    if len(token) > 4 and token.endswith("es"):
        stems.add(token[:-2])
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        stems.add(token[:-1])
    return stems


def _split(value: str) -> set[str]:
    """Split text into literal, stemmed, and explicitly synonymous token forms."""
    literal = {token for token in _literal_split(value) if token not in STOPWORDS}
    stemmed = set().union(*(_stems(token) for token in literal)) if literal else set()
    expanded = set(stemmed)
    for token in sorted(stemmed):
        expanded.update(TOKEN_SYNONYMS.get(token, ()))
    return {token for token in expanded if token not in STOPWORDS}


def _transformed_pair(task_tokens: set[str], candidate_tokens: set[str]) -> tuple[str, str] | None:
    """Return the first deterministic non-literal task-to-candidate token match."""
    if task_tokens & candidate_tokens:
        return None
    for task_token in sorted(task_tokens):
        task_forms = _split(task_token)
        for candidate_token in sorted(candidate_tokens):
            if task_forms & _split(candidate_token):
                return task_token, candidate_token
    return None


def _signals(task: str) -> dict[str, set[str]]:
    raw = re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*", task)
    excluded_literal: set[str] = set()
    for match in re.finditer(
        r"\b(?:instead of|rather than)\s+(?:the\s+)?([^.,;]+)",
        task,
        flags=re.IGNORECASE,
    ):
        excluded_literal.update(_literal_split(match.group(1)))
    excluded_terms = (
        set().union(*(_split(term) for term in excluded_literal))
        if excluded_literal
        else set()
    )
    literal_terms = _literal_split(task) - excluded_literal
    terms = _split(task) - excluded_terms
    if "find" in literal_terms and len(literal_terms) > 3:
        literal_terms.remove("find")
        terms -= _split("find")
    return {
        "paths": {x.replace("\\", "/") for x in raw if "/" in x or re.search(r"\.[A-Za-z0-9]{1,5}$", x)},
        "symbols": {x for x in raw if re.search(r"[A-Z]|_", x) and "/" not in x},
        "literal_terms": literal_terms,
        "terms": terms,
    }


def _is_underspecified_refactor(task: str) -> bool:
    lowered = task.casefold()
    broad_action = re.search(r"\b(?:clean up|improve|refactor)\b", lowered)
    preservation_only = re.search(
        r"\b(?:without changing (?:its )?(?:public )?behavio[u]?r|"
        r"preserv(?:e|ing) (?:every |all )?(?:existing )?contracts?|"
        r"keeping all contracts stable)\b",
        lowered,
    )
    return bool(broad_action and preservation_only)


def _role_order(roles: list[str]) -> list[PrimaryRole]:
    """Return deterministic roles with source owning mixed explicit work."""
    ordered: list[PrimaryRole] = []
    for role in ("source", "test", "configuration"):
        if role in roles:
            ordered.append(role)
    return ordered


def _explicit_path_roles(signals: dict[str, set[str]], files: list[dict[str, Any]], exact: bool) -> list[PrimaryRole]:
    matches: list[str] = []
    for path in signals["paths"]:
        for file in files:
            indexed = file["path"]
            if (indexed == path) if exact else (indexed.endswith("/" + path) or path.endswith("/" + indexed)):
                matches.append(file["role"])
    return _role_order(matches)


def _explicit_symbol_roles(signals: dict[str, set[str]], files: list[dict[str, Any]]) -> list[PrimaryRole]:
    return _role_order([file["role"] for file in files if set(file.get("symbols", [])) & signals["symbols"]])


def classify_task_intent(task: str, signals: dict[str, set[str]], files: list[dict[str, Any]]) -> TaskIntent:
    """Classify ownership using indexed evidence, then a scored rule table."""
    explicit = signals["paths"]
    lowered = task.lower().replace("_", " ").replace("-", " ").replace(".", " ")
    for roles, reason in (
        (_explicit_path_roles(signals, files, True), "explicit indexed path matched"),
        (_explicit_path_roles(signals, files, False), "explicit indexed path suffix matched"),
        (_explicit_symbol_roles(signals, files), "explicit indexed symbol matched"),
    ):
        if roles:
            primary = roles[0]
            explicit_secondary = tuple(role for role in roles[1:] if role != "source")
            matched = next(
                (
                    file["path"]
                    for file in files
                    if file["role"] == primary
                    and (file["path"] in explicit or any(file["path"].endswith("/" + path) for path in explicit) or set(file.get("symbols", [])) & signals["symbols"])
                ),
                primary,
            )
            return TaskIntent(primary, explicit_secondary, (f"{reason} {matched}",))

    scores: dict[PrimaryRole, int] = {role: 0 for role in ROLE_ORDER}
    matched_roles: set[PrimaryRole] = set()
    config_path = any(Path(path).suffix.lower() in CONFIG_EXTENSIONS or Path(path).name.lower() in CONFIG_NAMES for path in explicit)
    test_path = any("/test" in f"/{path.lower()}" or Path(path).name.lower().startswith("test_") for path in explicit)
    if config_path:
        scores["configuration"] = 300
        matched_roles.add("configuration")
    if test_path:
        scores["test"] = 300
        matched_roles.add("test")
    for pattern, role, weight in INTENT_RULES:
        if pattern.search(lowered):
            scores[role] = max(scores[role], weight)
            matched_roles.add(role)

    primary = min(ROLE_ORDER, key=lambda role: (-scores[role], ROLE_ORDER.index(role)))
    if not scores[primary]:
        return TaskIntent("source", (), ("ambiguous ownership defaults to source",))

    secondary: list[SecondaryRole] = []
    if primary == "source":
        if "configuration" in matched_roles:
            secondary.append("configuration")
        if "test" in matched_roles:
            secondary.append("test")
    reasons = [f"{primary} ownership rule scored {scores[primary]}"]
    reasons.extend(f"{role} work is a secondary constraint" for role in secondary)
    return TaskIntent(primary, tuple(secondary), tuple(reasons))


def _load(
    root: Path,
    out: Path | str | None,
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    directory = resolve_knowledge_directory(root, out, load_config(root))
    names = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json", "symbol-index.json"]
    if any(not (directory / x).is_file() for x in names):
        raise FileNotFoundError(
            "Knowledge artifacts missing at "
            f"{directory}\n"
            f"  → Run: python scripts/cli.py build --repo-root {root}\n"
            "  → Or:  Inspect source directly (knowledge is optional)"
        )
    manifest, repo, catalog, relationships, symbol_index = [
        json.loads((directory / x).read_text(encoding="utf-8")) for x in names
    ]
    errors = sum(
        (
            validate_schema_json(manifest, "manifest.schema.json"),
            validate_schema_json(repo, "repo-map.schema.json"),
            validate_schema_json(catalog, "symbols.schema.json"),
            validate_schema_json(relationships, "relationships.schema.json"),
            validate_schema_json(symbol_index, "symbol-index.schema.json"),
        ),
        [],
    )
    if errors:
        raise ValueError(f"Invalid knowledge artifacts: {errors}")
    return directory, manifest, repo, catalog, relationships, symbol_index


def _add(evidence: dict[str, tuple[float, str]], key: str, weight: float, family: str) -> None:
    if weight:
        evidence[key] = (weight, family)


def has_positive_evidence(candidate: dict[str, Any]) -> bool:
    """Whether a candidate has a positive score backed by positive evidence."""
    return candidate.get("score", 0) > 0 and any(weight > 0 for weight, _ in candidate.get("evidence", {}).values())


def _fallback_search(output_prefix: str, value: str, *, is_regex: bool = False) -> str:
    """Build one shell-safe fallback search from a literal value or regex pattern."""
    pattern = value if is_regex else rf"\b{re.escape(value)}\b"
    return f"rg -n --glob {shlex.quote('!' + output_prefix + '/**')} -- {shlex.quote(pattern)}"


def _lexical(
    files: list[dict[str, Any]],
    signals: dict[str, set[str]],
    weights: dict[str, float],
    freshness: str,
    configuration_keys: dict[str, list[str]] | None = None,
    descriptions: dict[str, set[str]] | None = None,
    source_terms: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    configuration_keys = configuration_keys or {}
    descriptions = descriptions or {}
    source_terms = source_terms or {}
    results = []
    for file in files:
        path = file["path"]
        evidence: dict[str, tuple[float, str]] = {}
        names = file.get("symbols", [])
        exact = [x for x in names if x in signals["symbols"]]
        if any(path == x or path.endswith("/" + x) for x in signals["paths"]):
            _add(evidence, f"exact_path: {path}", weights["exact_path"], "path")
        if exact:
            _add(evidence, f"exact_symbol: {exact[0]}", weights["exact_symbol"], "identifier")
        path_stem_terms = _literal_split(Path(path).stem)
        matched = signals["literal_terms"] & path_stem_terms
        expanded_filename_matches = {
            term
            for term in path_stem_terms
            if _split(term) & signals["terms"]
        }
        if matched or expanded_filename_matches:
            filename_matches = matched or expanded_filename_matches
            _add(
                evidence,
                f"filename: {sorted(filename_matches)[0]}",
                weights["filename"],
                "path",
            )
            if len(expanded_filename_matches) > 1:
                _add(
                    evidence,
                    f"filename_coverage: {','.join(sorted(expanded_filename_matches))}",
                    weights["filename"] * 3 * (len(expanded_filename_matches) - 1),
                    "path",
                )
        role_hints = {
            "model": {"model", "schema", "shape"},
            "repository": {"adapter", "lookup", "persistence", "repository", "storage", "store"},
            "service": {
                "activate",
                "activated",
                "application",
                "behavior",
                "implementation",
                "normalize",
                "normalization",
                "process",
                "produce",
                "service",
            },
            "policy": {"comparison", "policy", "rule", "threshold"},
            "handler": {"delivery", "handler", "payload"},
            "matcher": {"match", "matches", "matching", "matcher", "targeting"},
            "orchestrator": {
                "billing",
                "cycle",
                "orchestrator",
                "primary",
                "propagation",
                "retries",
                "retry",
                "workflow",
            },
        }
        stem = Path(path).stem.casefold()
        for suffix, hints in role_hints.items():
            if stem.endswith("_" + suffix) and signals["terms"] & hints:
                multiplier = 3 if suffix == "orchestrator" else 1
                _add(
                    evidence,
                    f"filename_role: {suffix}",
                    weights["filename"] * multiplier,
                    "path",
                )
        symbol_terms = set().union(*(_literal_split(x) for x in names)) if names else set()
        matched = {
            term
            for term in symbol_terms
            if _split(term) & signals["terms"]
        }
        if matched:
            _add(evidence, f"symbol_token: {sorted(matched)[0]}", weights["symbol_token"], "identifier")
            if len(matched) > 1:
                _add(
                    evidence,
                    f"symbol_coverage: {','.join(sorted(matched))}",
                    weights["symbol_token"] * (min(3, len(matched)) - 1),
                    "identifier",
                )
        description_matches = {
            term
            for term in descriptions.get(path, set())
            if _split(term) & signals["terms"]
        }
        if description_matches:
            _add(
                evidence,
                f"description: {','.join(sorted(description_matches)[:3])}",
                weights["symbol_token"] * min(2, len(description_matches)),
                "description",
            )
        source_matches = {
            term
            for term in source_terms.get(path, set())
            if _split(term) & signals["terms"]
        }
        if source_matches:
            _add(
                evidence,
                f"source_token: {','.join(sorted(source_matches)[:2])}",
                weights["symbol_token"] * min(2, len(source_matches)),
                "source_token",
            )
        semantic_concepts = (
            expanded_filename_matches
            | matched
            | description_matches
            | source_matches
        )
        if len(semantic_concepts) > 1:
            _add(
                evidence,
                f"semantic_coverage: {','.join(sorted(semantic_concepts)[:4])}",
                weights["filename"] * 2 * (min(4, len(semantic_concepts)) - 1),
                "semantic_coverage",
            )
        subsystem_terms = _literal_split(file["subsystem"])
        matched = signals["literal_terms"] & subsystem_terms
        if matched:
            _add(evidence, f"subsystem: {sorted(matched)[0]}", weights["subsystem"], "subsystem")
        path_terms = _literal_split(path)
        matched = signals["literal_terms"] & path_terms
        if matched:
            _add(evidence, f"text_match: {sorted(matched)[0]}", weights["text_match"], "path")
        candidate_terms = path_terms | path_stem_terms | symbol_terms | subsystem_terms
        transformed = _transformed_pair(signals["literal_terms"], candidate_terms)
        if transformed:
            _add(
                evidence,
                f"synonym_token: {transformed[0]}\N{RIGHTWARDS ARROW}{transformed[1]}",
                weights["synonym_token"],
                "synonym_token",
            )
        config_key_terms = (
            set().union(
                *(_literal_split(key) for key in configuration_keys.get(path, []))
            )
            if configuration_keys.get(path)
            else set()
        )
        config_matches = {
            term
            for term in config_key_terms
            if _split(term) & signals["terms"]
        }
        if file["role"] == "configuration" and config_matches:
            _add(
                evidence,
                f"configuration_key: {sorted(config_matches)[0]}",
                weights["configuration"],
                "configuration_key",
            )
            if len(config_matches) > 1:
                _add(
                    evidence,
                    f"configuration_coverage: {','.join(sorted(config_matches))}",
                    weights["configuration"] * (min(3, len(config_matches)) - 1),
                    "configuration_key",
                )
        if file["role"] == "configuration" and (
            file["path"] in signals["paths"] or signals["terms"] & STRONG_CONFIG_TOKENS
        ):
            _add(evidence, f"configuration: {path}", weights["configuration"], "configuration")
        if file.get("generated"):
            _add(evidence, "generated_penalty", weights["generated_penalty"], "generated_penalty")
        if "vendor" in path.lower() or "node_modules" in path.lower():
            _add(evidence, "vendor_penalty", weights["vendor_penalty"], "vendor_penalty")
        if not file.get("language") and file["role"] == "source":
            _add(
                evidence,
                "unsupported_extractor_penalty",
                weights["unsupported_extractor_penalty"],
                "unsupported_extractor_penalty",
            )
        if freshness != "fresh":
            _add(evidence, "stale_knowledge_penalty", weights["stale_knowledge_penalty"], "stale_knowledge_penalty")
        score = sum(x[0] for x in evidence.values())
        if score > 0:
            results.append({"file": file, "score": score, "evidence": evidence})
    return sorted(results, key=lambda x: (-x["score"], x["file"]["path"]))


def _rerank(
    shortlist: list[dict[str, Any]], relationships: dict[str, Any], by_path: dict[str, Any], weights: dict[str, float]
) -> list[dict[str, Any]]:
    selected = {x["file"]["path"]: x for x in shortlist}
    seed = set(selected)
    # Include direct neighbours only; this is the sole controlled expansion.
    for edge in relationships.get("imports", []):
        if edge["source"] in seed or edge["target"] in seed:
            other = edge["target"] if edge["source"] in seed else edge["source"]
            if other in by_path and other not in selected:
                selected[other] = {"file": by_path[other], "score": 0.0, "evidence": {}}
    tests_by_target: dict[str, list[str]] = {}
    for edge in relationships.get("test_links", []):
        tests_by_target.setdefault(edge["target"], []).append(edge["source"])
    for path, item in selected.items():
        ev = item["evidence"]
        for test in sorted(tests_by_target.get(path, [])):
            _add(ev, f"tested_by: {test}", weights["related_test"], "related_test")
        for importer in sorted(relationships.get("reverse_imports", {}).get(path, [])):
            _add(
                ev,
                f"imported_by: {importer}",
                weights["reverse_import_relationship"],
                "reverse_import_relationship",
            )
        for edge in relationships.get("imports", []):
            if edge["source"] == path:
                _add(ev, f"imports: {edge['target']}", weights["import_relationship"], "import_relationship")
        if Path(path).name.lower() in {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}:
            _add(ev, f"entry_point: {path}", weights["entry_point"], "entry_point")
        item["score"] = sum(x[0] for x in ev.values())
    return sorted((x for x in selected.values() if x["score"] > 0), key=lambda x: (-x["score"], x["file"]["path"]))


def _symbols(directory: Path, catalog: dict[str, Any], paths: set[str]) -> dict[str, list[dict[str, Any]]]:
    answer: dict[str, list[dict[str, Any]]] = {x: [] for x in paths}
    wanted = {shard_id(x) for x in paths}
    for shard in catalog["shards"]:
        if shard["id"] in wanted:
            for symbol in json.loads((directory / shard["path"]).read_text())["symbols"]:
                if symbol["path"] in answer:
                    answer[symbol["path"]].append(symbol)
    return answer


def _exact_symbol_paths(symbol_index: dict[str, Any], signals: dict[str, set[str]]) -> set[str]:
    """Return exact symbol owners without loading symbol shards."""
    candidates = signals["symbols"] | signals["literal_terms"]
    return {
        entry["file"]
        for candidate in candidates
        for entry in symbol_index.get("symbols", {}).get(candidate.casefold(), [])
    }


def _configuration_key_candidates(task: str) -> list[str]:
    """Extract ordered key-shaped candidates without treating prose as keys."""
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", task)
    dotted = re.findall(r"\b(?:[A-Za-z][\w-]*\.)+[A-Za-z][\w-]*\b", task)
    hyphenated = re.findall(r"\b[a-z][a-z0-9]*(?:[-_][a-z0-9]+)+\b", task.lower())
    phrases = [phrase for phrase in CONFIG_PHRASES if phrase in task.lower().replace("-", " ")]
    strong = sorted(term for term in _literal_split(task) if len(term) > 3 and term not in STOPWORDS)
    return list(dict.fromkeys(quoted + dotted + hyphenated + phrases + strong))


def _configuration_fallback_pattern(key: str) -> str:
    """Return a regex that searches for one configuration assignment key."""
    return rf"{re.escape(key)}\s*[:=]"


def _configuration_fallback_candidates(task: str, signals: dict[str, set[str]]) -> list[str]:
    """Return ordered, task-derived configuration keys without filename fragments."""
    configuration_paths = {
        path for path in signals["paths"]
        if "/" in path or Path(path).suffix.lower() in CONFIG_EXTENSIONS or Path(path).name.lower() in CONFIG_NAMES
    }
    path_values = {path.lower() for path in configuration_paths}
    path_terms = set().union(*(_literal_split(path) for path in configuration_paths)) if configuration_paths else set()
    ignored = {"config", "configuration", "project"}
    candidates = []
    for candidate in _configuration_key_candidates(task):
        normalized = candidate.lower().replace("\\", "/")
        candidate_terms = _literal_split(candidate)
        if normalized in path_values or (candidate_terms and candidate_terms <= path_terms) or normalized in ignored:
            continue
        candidates.append(candidate)
    return list(dict.fromkeys(candidates))


def _configuration_match_score(line: str, candidate: str) -> int:
    """Rank active structural key matches above values, comments, and prose."""
    stripped = line.strip()
    if stripped.startswith(("#", ";", "//")):
        return -100
    normalized = candidate.lower().replace("-", "_")
    comparable = stripped.lower().replace("-", "_")
    escaped = re.escape(normalized)
    if re.match(rf'^\s*"?{escaped}"?\s*[=:]', comparable):
        return 90 if "." in normalized else 80
    if re.match(rf"^\s*{escaped}\s*=", comparable):
        return 85
    if re.match(rf'^\s*"{escaped}"\s*:', comparable):
        return 82
    key = normalized.rsplit(".", 1)[-1]
    if "." in normalized and re.match(rf"^\s*\[.*{re.escape(normalized.rsplit('.', 1)[0])}.*\]", comparable):
        return 45
    if re.match(rf'^\s*"?{re.escape(key)}"?\s*[=:]', comparable):
        return 70
    if re.search(rf"\b{escaped}\b", comparable):
        return 15
    return 0


def _structured_configuration_keys(path: str, lines: list[str]) -> dict[int, str]:
    """Track the small amount of structure needed to rank active config keys."""
    suffix = Path(path).suffix.lower()
    result: dict[int, str] = {}
    if Path(path).name.lower() in {"makefile", "gnumakefile"}:
        for index, line in enumerate(lines):
            match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", line)
            if match:
                result[index] = match.group(1)
        return result
    if suffix in {".toml", ".ini", ".cfg"}:
        section = ""
        for index, line in enumerate(lines):
            match = re.match(r"\s*\[([^]]+)\]", line)
            if match:
                section = match.group(1).strip()
            match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*[=:]", line)
            if match and not line.lstrip().startswith(("#", ";")):
                result[index] = ".".join(part for part in (section, match.group(1)) if part)
        return result
    if suffix in {".yaml", ".yml"}:
        yaml_ancestors: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = re.match(r"^(\s*)([A-Za-z0-9_.-]+):", line)
            if not match or line.lstrip().startswith("#"):
                continue
            indent, key = len(match.group(1).expandtabs(2)), match.group(2)
            while yaml_ancestors and yaml_ancestors[-1][0] >= indent:
                yaml_ancestors.pop()
            result[index] = ".".join([name for _, name in yaml_ancestors] + [key])
            yaml_ancestors.append((indent, key))
        return result
    if suffix == ".json":
        json_ancestors: list[str] = []
        for index, line in enumerate(lines):
            match = re.match(r'\s*"([^"\\]+)"\s*:', line)
            if match:
                key = match.group(1)
                result[index] = ".".join(json_ancestors + [key])
                if "{" in line[line.find(":") + 1:]:
                    json_ancestors.append(key)
            closes = line.count("}")
            for _ in range(min(closes, len(json_ancestors))):
                json_ancestors.pop()
        return result
    return result


def _focused_text_range(root: Path, path: str, task: str, config: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    """Return the highest-ranked compact, active configuration-key range."""
    try:
        lines = (root / path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None, None, None
    ranked = []
    structured = _structured_configuration_keys(path, lines)
    for candidate in _configuration_key_candidates(task):
        for index, line in enumerate(lines):
            score = _configuration_match_score(line, candidate)
            normalized = candidate.lower().replace("-", "_")
            structure = structured.get(index, "").lower().replace("-", "_")
            if structure == normalized:
                score = 120 if "." in normalized else 110
            elif Path(path).suffix.lower() == ".json" and "." in candidate:
                quoted_parts = [f'"{part}"' for part in candidate.split(".")]
                positions = [line.find(part) for part in quoted_parts]
                if all(position >= 0 for position in positions) and positions == sorted(positions):
                    score = 120
            elif structure.rsplit(".", 1)[-1:] == normalized.rsplit(".", 1)[-1:] and score >= 70:
                score = max(score, 100)
            if "." in candidate and score < 75:
                key = candidate.rsplit(".", 1)[-1].replace("-", "_")
                if re.match(rf"^\s*{re.escape(key)}\s*[=:]", line.strip().lower().replace("-", "_")):
                    section = candidate.rsplit(".", 1)[0].replace("-", "_")
                    if any(section in prior.strip().lower().replace("-", "_") for prior in lines[max(0, index - 8):index]):
                        score = 95
            ranked.append((score, index, candidate))
    score, index, needle = max(ranked, default=(0, 0, ""), key=lambda item: (item[0], -item[1], item[2]))
    if score >= 70:
        start = index
        for prior in range(index - 1, max(-1, index - 9), -1):
            previous = lines[prior].strip()
            if previous.startswith("[") or (previous.endswith(":") and not previous.startswith(("#", ";", "//"))):
                start = prior
                break
        limit = config["max_context_lines"]
        start = max(0, start - min(2, limit // 4))
        end = min(len(lines), index + 1 + min(4, limit - 1))
        if end - start > limit:
            end = start + limit
        return start + 1, end, needle
    return None, None, None


def _target(
    candidate: dict[str, Any], symbols: list[dict[str, Any]], signals: dict[str, set[str]], root: Path, task: str, config: dict[str, Any]
) -> dict[str, Any]:
    def symbol_relevance(symbol: dict[str, Any]) -> tuple[int, int]:
        exact = symbol["name"] in signals["symbols"]
        name_matches = _split(symbol["name"]) & signals["terms"]
        docstring_matches = _split(str(symbol.get("docstring", ""))) & signals["terms"]
        behavioral = bool(
            re.match(
                r"^(?:activate|apply|execute|handle|match|may|permit|process|resolve|run|validate)",
                symbol["name"],
            )
        )
        score = (
            (100 if exact else 0)
            + len(name_matches) * 10
            + min(2, len(docstring_matches)) * 3
            + (15 if behavioral else 0)
        )
        return score, -int(symbol["line_start"])

    ranked_symbols = sorted(
        (symbol for symbol in symbols if symbol_relevance(symbol)[0] > 0),
        key=symbol_relevance,
        reverse=True,
    )
    match = ranked_symbols[0] if ranked_symbols else None
    file = candidate["file"]
    start_line = match["line_start"] if match else None
    end_line = match["line_end"] if match else None
    focused_key = None
    if not match and file["role"] == "configuration":
        start_line, end_line, focused_key = _focused_text_range(root, file["path"], task, config)
    evidence = [key for key, (weight, _) in sorted(candidate["evidence"].items()) if weight > 0]
    if focused_key:
        evidence.append(f"configuration_key: {focused_key}")
    return {
        "path": file["path"],
        "symbol": match["name"] if match else None,
        "start_line": start_line,
        "end_line": end_line,
        "role": file["role"],
        "evidence": sorted(set(evidence)),
        "question": f"Does {match['name'] if match else file['path']} own the requested behavior?",
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for item in items:
        old = output.get(item["path"])
        if not old:
            output[item["path"]] = item
        else:
            old["evidence"] = sorted(set(old["evidence"]) | set(item["evidence"]))
    return [output[path] for path in sorted(output)]


def evidence_for_test_target(test_path: str, source_path: str) -> str:
    """Evidence from the returned test target's perspective."""
    del test_path
    return f"tests: {source_path}"


def evidence_for_import_neighbor(primary_path: str, source_path: str, target_path: str) -> tuple[str, str]:
    """Return the target and its directional import evidence for one graph edge."""
    if source_path == primary_path:
        return target_path, f"dependency_of: {primary_path}"
    return source_path, f"imports: {primary_path}"


def _relationship_targets(
    primary_paths: set[str], relationships: dict[str, Any], by_path: dict[str, Any], root: Path, task: str,
    signals: dict[str, set[str]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return deterministic direct neighbours with evidence from the neighbour's perspective."""
    merged: dict[str, dict[str, Any]] = {}
    for edge in relationships.get("imports", []):
        source, target = edge["source"], edge["target"]
        if source in primary_paths and target not in primary_paths:
            adjacent, evidence = evidence_for_import_neighbor(source, source, target)
        elif target in primary_paths and source not in primary_paths:
            adjacent, evidence = evidence_for_import_neighbor(target, source, target)
        else:
            continue
        if adjacent not in by_path:
            continue
        item = merged.setdefault(adjacent, {"file": by_path[adjacent], "evidence": {}})
        _add(
            item["evidence"],
            evidence,
            config["weights"]["import_relationship"],
            "import_relationship",
        )
    return _dedupe([_target(item, [], signals, root, task, config) for _, item in sorted(merged.items())])


def _estimate_tokens_saved(root: Path, repo: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Estimate tokens saved by returning only targets instead of all files."""
    all_files = repo.get("files", [])
    total_files = len(all_files)

    # Estimate average tokens per file from a sample (up to 20 files)
    sample_paths = [f["path"] for f in all_files[:20]]
    sample_tokens = []
    for path in sample_paths:
        try:
            content = (root / path).read_text(encoding="utf-8", errors="ignore")
            sample_tokens.append(count_tokens(content))
        except OSError:
            continue
    avg_tokens = sum(sample_tokens) // max(len(sample_tokens), 1)

    target_tokens = sum(_target_tokens(root, target) for target in targets)

    total_estimated = avg_tokens * total_files
    return {
        "target_tokens": target_tokens,
        "total_estimated_tokens": total_estimated,
        "tokens_saved": max(0, total_estimated - target_tokens),
        "reduction_percent": round(100 * (1 - target_tokens / max(total_estimated, 1)), 1),
    }


def _target_tokens(root: Path, target: dict[str, Any]) -> int:
    """Count only the source range represented by one resolver target."""
    try:
        lines = (root / target["path"]).read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    except OSError:
        return 0
    start = max(int(target.get("start_line") or 1), 1)
    end = min(int(target.get("end_line") or len(lines)), len(lines))
    return count_tokens("".join(lines[start - 1:end])) if end >= start else 0


def _apply_budget(
    root: Path,
    phases: dict[int, dict[str, Any]],
    phase: int | str,
    budget: int,
) -> dict[str, Any] | None:
    if budget < 0:
        raise ValueError("budget must be zero or a positive integer")
    if budget == 0:
        return None
    used = 0
    excluded: list[dict[str, Any]] = []
    selected = (1, 2, 3) if phase == "all" else (int(phase),)
    for key in selected:
        retained = []
        for target in phases[key]["targets"]:
            tokens = _target_tokens(root, target)
            if used + tokens <= budget:
                retained.append(target)
                used += tokens
            else:
                excluded.append({"phase": key, "path": target["path"], "tokens": tokens})
        phases[key]["targets"] = retained
    return {
        "limit": budget,
        "used": used,
        "excluded_targets": excluded,
    }


def resolve_task(
    repo_root: Path | str, task: str, knowledge_dir: Path | str | None = None, phase: int | str = 1,
    budget: int = 0,
    record_analytics: bool = False,
) -> dict[str, Any]:
    if phase not in {1, 2, 3, "all"}:
        raise ValueError("phase must be 1, 2, 3, or all")
    root = Path(repo_root).resolve()
    directory, _, repo, catalog, relationships, symbol_index = _load(root, knowledge_dir)
    config = load_config(root)
    freshness = check_freshness(root, directory)["status"]
    signals = _signals(task)
    by_path = {x["path"]: x for x in repo["files"]}
    intent = classify_task_intent(task, signals, repo["files"])
    configuration_keys = {
        item["path"]: item.get("keys", [])
        for item in repo.get("configurations", [])
    }
    lexical_matches = _lexical(
        repo["files"],
        signals,
        config["weights"],
        freshness,
        configuration_keys,
        {},
    )
    content_candidates = {
        item["file"]["path"] for item in lexical_matches[:24]
    } | _exact_symbol_paths(symbol_index, signals)
    indexed_symbols = _symbols(directory, catalog, content_candidates)
    descriptions = {
        path: (
            set().union(*(_literal_split(str(symbol.get("docstring", ""))) for symbol in symbols))
            if symbols
            else set()
        )
        for path, symbols in indexed_symbols.items()
    }
    source_terms = {
        path: _literal_split(
            (root / path).read_text(encoding="utf-8", errors="ignore")
        )
        for path in content_candidates
    }
    rescored_candidates = _lexical(
        [by_path[path] for path in sorted(content_candidates)],
        signals,
        config["weights"],
        freshness,
        configuration_keys,
        descriptions,
        source_terms,
    )
    rescored_by_path = {
        item["file"]["path"]: item
        for item in rescored_candidates
    }
    lexical_matches = sorted(
        (
            rescored_by_path.get(item["file"]["path"], item)
            for item in lexical_matches
        ),
        key=lambda item: (-item["score"], item["file"]["path"]),
    )
    literal_primary_matches = [
        item
        for item in lexical_matches
        if item["file"]["role"] == intent.primary_role
        and any(weight > 0 and family != "synonym_token" for weight, family in item["evidence"].values())
    ]
    primary_lexical = (literal_primary_matches or lexical_matches)[:8]
    lexical = list(
        {
            item["file"]["path"]: item
            for item in [*primary_lexical, *lexical_matches[:8]]
        }.values()
    )
    ranked = _rerank(lexical, relationships, by_path, config["weights"])
    lexical_paths = {item["file"]["path"] for item in primary_lexical}
    primaries = [
        item for item in ranked
        if item["file"]["path"] in lexical_paths
        and item["file"]["role"] == intent.primary_role
        and has_positive_evidence(item)
    ][:3]
    exact_symbol_primaries = [
        item
        for item in primaries
        if any(label.startswith("exact_symbol:") for label in item["evidence"])
    ]
    if exact_symbol_primaries:
        primaries = exact_symbol_primaries
    if _is_underspecified_refactor(task):
        primaries = []
    primary_symbol_paths = {x["file"]["path"] for x in primaries}
    missing_symbol_paths = primary_symbol_paths - set(indexed_symbols)
    if missing_symbol_paths:
        indexed_symbols.update(_symbols(directory, catalog, missing_symbol_paths))
    symbol_map = {path: indexed_symbols[path] for path in primary_symbol_paths}
    primary = [_target(x, symbol_map[x["file"]["path"]], signals, root, task, config) for x in primaries]
    primary_paths = {x["path"] for x in primary}
    tests = _dedupe(
        [
            _target(
                {
                    "file": by_path[x["source"]],
                    "evidence": {
                        evidence_for_test_target(x["source"], x["target"]): (config["weights"]["related_test"], "test")
                    },
                },
                [],
                signals, root, task, config,
            )
            for x in relationships.get("test_links", [])
            if x["target"] in primary_paths
        ]
    )
    impacts = _relationship_targets(primary_paths, relationships, by_path, root, task, signals, config)
    score = primaries[0]["score"] if primaries else 0
    margin = score - (primaries[1]["score"] if len(primaries) > 1 else 0)
    families = (
        {
            family
            for weight, family in primaries[0]["evidence"].values()
            if weight > 0
        }
        if primaries
        else set()
    )
    focused = bool(primary and primary[0]["start_line"])
    strong_labels: list[str] = []
    if primaries:
        evidence = primaries[0]["evidence"]
        if any(label.startswith("exact_path:") and weight > 0 for label, (weight, _) in evidence.items()):
            strong_labels.append("exact_path")
        for label, (weight, _) in evidence.items():
            if label.startswith("exact_symbol:") and weight > 0:
                symbol = label.split(":", 1)[1].strip()
                owners = sum(symbol in file.get("symbols", []) for file in repo["files"])
                if owners == 1:
                    strong_labels.append("exact_symbol")
            if label.startswith("filename:") and weight > 0:
                term = label.split(":", 1)[1].strip()
                owners = sum(term in _literal_split(Path(file["path"]).stem) for file in repo["files"])
                if owners == 1 and term not in WEAK_FILENAME_TERMS:
                    strong_labels.append("filename")
    has_strong_evidence = bool(strong_labels)
    high = (
        freshness == "fresh"
        and focused
        and margin >= config["confidence_margin"]
        and len(families) >= 2
        and has_strong_evidence
        and "exact_symbol" not in strong_labels
    )
    level = "high" if high else "medium" if primary else "low"
    terms = sorted(signals["terms"])
    output_prefix = knowledge_output_prefix(root, directory)
    strongest = sorted(
        {value for value in signals["symbols"] | signals["terms"] if value.lower() not in STOPWORDS},
        key=lambda value: (-len(value), value),
    )
    fallback_values: list[tuple[str, bool]]
    if intent.primary_role == "configuration" and ((primary and not focused) or not primary):
        configuration_candidates = _configuration_fallback_candidates(task, signals)
        fallback_values = [(_configuration_fallback_pattern(configuration_candidates[0]), True)] if configuration_candidates else []
        if not primary:
            fallback_values.extend((candidate, False) for candidate in configuration_candidates[1:])
    else:
        fallback_values = [(term, False) for term in strongest]
    fallback = []
    if not high:
        limit = 1 if level == "medium" else 3
        fallback = list(
            dict.fromkeys(
                _fallback_search(output_prefix, value, is_regex=is_regex)
                for value, is_regex in fallback_values[:limit]
            )
        )
    if not primary:
        reasons = ["no indexed owner matched the task terms"]
        uncertainties = ["run the targeted fallback search against authoritative source"]
    else:
        evidence_labels = primary[0]["evidence"]
        concrete = [label.replace("exact_symbol: ", "exact symbol matched ") for label in evidence_labels if label.startswith("exact_symbol:")]
        concrete += [label.replace("tested_by: ", "direct test relationship points to ") for label in evidence_labels if label.startswith("tested_by:")]
        reasons = concrete or [f"{primary[0]['role']} candidate matched task vocabulary"]
        uncertainties = []
        if primary[0]["role"] == "configuration" and not focused:
            uncertainties.append("no exact configuration key or focused range was located")
        if len(primaries) > 1 and margin < config["confidence_margin"]:
            uncertainties.append("candidate score separation is below the configured confidence margin")
        if len(families) < 2:
            uncertainties.append("no direct test, import, or entry-point evidence separates candidates")
        if not has_strong_evidence:
            uncertainties.append("no exact symbol, exact path, or filename evidence supports high confidence")
        if high:
            reasons.append("top candidate exceeds the configured confidence margin")
    phases: dict[int, dict[str, Any]] = {
        1: {
            "targets": primary,
            "question": "Which likely task owner owns the requested behavior or constraint?",
            "stop_condition": "Stop when ownership and the source contract are verified.",
            "expansion_triggers": ["ownership remains ambiguous", "source contradicts the index"],
        },
        2: {
            "targets": _dedupe(
                tests
                + [
                    _target(item, [], signals, root, task, config)
                    for item in ranked
                    if item["file"]["role"] in set(intent.secondary_roles)
                    and item["file"]["path"] not in primary_paths
                    and has_positive_evidence(item)
                ]
            )[:3],
            "question": "Which direct tests, configuration, or represented constraints constrain the change?",
            "stop_condition": "Stop when direct constraints are understood.",
            "expansion_triggers": ["a compatibility constraint is unresolved"],
        },
        3: {
            "targets": impacts[:3],
            "question": "Which first-order callers or dependencies are affected?",
            "stop_condition": "Stop when affected contracts are explicit.",
            "expansion_triggers": ["cross-subsystem behavior is observed"],
        },
    }
    budget_detail = _apply_budget(root, phases, phase, budget)
    if budget_detail and budget_detail["excluded_targets"]:
        uncertainties.append(
            f"{len(budget_detail['excluded_targets'])} owner or constraint target(s) were excluded by the token budget"
        )
    selected_targets: list[dict[str, Any]] = (
        phases[int(phase)]["targets"] if phase != "all" else phases[1]["targets"]
    )
    payload = {
        "_meta": {
            "command": "resolve",
            "schema": "resolver-result.schema.json",
            "docs": "references/resolver-design.md",
        },
        "task": task,
        "phase": phase,
        "knowledge_freshness": freshness,
        "task_terms": terms,
        "task_intent": {
            "primary_role": intent.primary_role,
            "secondary_roles": list(intent.secondary_roles),
            "reasons": list(intent.reasons),
        },
        "confidence": {"level": level, "score": round(score, 3), "reasons": reasons, "uncertainties": uncertainties},
        "tokens_saved_estimate": _estimate_tokens_saved(root, repo, selected_targets),
        "fallback_searches": fallback,
    }
    if budget_detail is not None:
        payload["budget_detail"] = budget_detail
    payload.update(
        {"phases": [{"phase": key, **value} for key, value in phases.items()]}
        if phase == "all"
        else {"phase": int(phase), **phases[int(phase)]}
    )
    errors = validate_schema_json(payload, "resolver-result.schema.json")
    if errors:
        raise ValueError(f"Invalid resolver result: {errors}")

    if record_analytics:
        try:
            from analytics import record_session

            returned_targets = (
                [target for phase_payload in payload["phases"] for target in phase_payload["targets"]]
                if phase == "all"
                else payload["targets"]
            )
            record_session(directory, "resolve", {
                "task": task,
                "phase": phase,
                "confidence": level,
                "targets_returned": len(returned_targets),
                "tokens_saved": payload.get("tokens_saved_estimate", {}).get("tokens_saved", 0),
            })
        except Exception:
            pass

    return payload


def format_human(result: dict[str, Any]) -> str:
    targets = result.get("targets", []) if result.get("phase") != "all" else result["phases"][0]["targets"]
    return "\n".join(
        [
            f"# Task Resolution: {result['task']}",
            f"Confidence: {result['confidence']['level']}",
            *[f"- `{x['path']}:{x['start_line'] or '?'}-{x['end_line'] or '?'}` {x['symbol'] or ''}" for x in targets],
        ]
    )


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    """Strip scoring breakdowns to return minimal agent-facing output."""
    compact: dict[str, Any] = {
        "task": result["task"],
        "phase": result["phase"],
        "confidence": result["confidence"]["level"],
    }
    if result.get("phase") == "all":
        compact["phases"] = [
            {
                "phase": p["phase"],
                "targets": [t["path"] for t in p.get("targets", [])],
            }
            for p in result.get("phases", [])
        ]
    else:
        compact["targets"] = [t["path"] for t in result.get("targets", [])]
        if result.get("stop_condition"):
            compact["stop_condition"] = result["stop_condition"]
    if result.get("fallback_searches"):
        compact["fallback_searches"] = result["fallback_searches"]
    if result.get("tokens_saved_estimate"):
        compact["tokens_saved_estimate"] = result["tokens_saved_estimate"]
    if result.get("budget_detail"):
        compact["budget_detail"] = result["budget_detail"]
    return compact


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="1")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()
    result = resolve_task(
        args.repo_root, args.task, args.output, args.phase if args.phase == "all" else int(args.phase)
    )
    print(json.dumps(result, indent=2) if args.format == "json" else format_human(result))
