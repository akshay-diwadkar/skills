"""Deterministic parsing for contrastive repository task queries."""

from __future__ import annotations

import re

from resolver.schemas import OwnerCardinality, TaskQuery

COMPONENT_ALIASES = {
    "controller": "route/controller",
    "route": "route/controller",
    "routes": "route/controller",
    "docs": "documentation",
    "doc": "documentation",
    "generated": "generated",
    "legacy": "legacy",
    "migration": "migration",
    "migrations": "migration",
    "policy": "policy",
    "service": "service",
    "handler": "handler",
    "job": "job",
    "worker": "job",
    "repository": "repository",
    "adapter": "adapter",
    "client": "client",
    "model": "model",
    "orchestrator": "orchestrator",
    "orchestration": "orchestrator",
    "receiver": "receiver",
    "receivers": "receiver",
    "processor": "processor",
    "processors": "processor",
    "router": "processor",
    "routing": "processor",
    "exporter": "exporter",
    "exporters": "exporter",
    "transform": "transform",
    "distribution": "distribution",
    "distributions": "distribution",
    "plugin": "plugin",
    "plugins": "plugin",
    "command": "command",
    "schema": "schema",
    "documentation": "documentation",
}
GENERIC_ROOTS = frozenset({"src", "app", "lib", "source", "code"})
ROLE_WORDS = {"test": "test", "tests": "test", "implementation": "source", "configuration": "configuration"}
INTENT_WORDS = {
    "owner": "ownership",
    "implementation": "ownership",
    "constraint": "constraint",
    "test": "constraint",
    "caller": "impact",
    "callers": "impact",
    "dependency": "impact",
    "dependencies": "impact",
    "impact": "impact",
}
CONCEPT_GROUPS = (
    frozenset({"cap", "ceiling", "limit", "maximum"}),
    frozenset({"gradual", "percentage", "progressive", "rollout"}),
    frozenset({"schedule", "scheduled", "scheduling"}),
    frozenset({"fetch", "lookup", "retrieve", "retrieval"}),
    frozenset({"adapter", "persist", "persistence", "store", "storage"}),
    frozenset({"job", "jobs", "queue", "worker", "workers"}),
    frozenset({"choice", "option", "options"}),
    frozenset({"typescript", "tsconfig", "compiler"}),
    frozenset({"linter", "lint", "ruff"}),
    frozenset({"npm", "package", "script", "scripts"}),
)
STOPWORDS = frozenset({
    "a", "an", "and", "the", "to", "of", "for", "from", "in", "on", "with",
    "find", "locate", "determine", "identify", "which", "file", "code", "current",
    "after", "are", "at", "before", "even", "exactly", "is", "its", "owner",
    "owns", "responsible", "source", "that", "though", "users", "or", "if",
    "when", "does", "tracked", "direct", "evidence", "absent", "abstain",
})
NEGATIVE_PATTERN = re.compile(
    r"\b(?:not|rather\s+than|instead\s+of|exclud(?:e|ing)|ignor(?:e|ing))\s+(?:the\s+)?"
    r"(?P<value>[^,.;]+?)(?=\s+\b(?:and|but)\b|[,.;]|$)",
    re.IGNORECASE,
)


def _tokens(value: str) -> list[str]:
    compounds = [
        raw.casefold()
        for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", value)
        if re.search(r"[a-z0-9][A-Z]", raw)
    ]
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[_/\\.-]+", " ", normalized)
    result: list[str] = compounds
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", normalized):
        token = raw.casefold()
        if token in STOPWORDS:
            continue
        result.append(token)
        if len(token) > 4 and token.endswith("ies"):
            result.append(token[:-3] + "y")
        elif len(token) > 4 and token.endswith("ed"):
            result.extend((token[:-1], token[:-2]))
        elif len(token) > 4 and token.endswith("ing"):
            result.extend((token[:-3], token[:-3] + "e"))
        elif len(token) > 4 and token.endswith("es"):
            result.extend((token[:-1], token[:-2]))
        elif len(token) > 4 and token.endswith("s"):
            result.append(token[:-1])
    return result


def _component(tokens: list[str]) -> str | None:
    # Distribution is a distinct assembly surface, not a receiver/exporter
    # mention inside a registration question.
    if any(token in {"distribution", "distributions"} for token in tokens):
        return "distribution"
    if "policy" in tokens:
        return "policy"
    explicit = [
        COMPONENT_ALIASES[token]
        for token in tokens
        if token in COMPONENT_ALIASES and token not in {"route", "routes", "router", "routing"}
    ]
    if explicit:
        return explicit[-1]
    # The stemmer emits both ``routing`` and ``route``. Preserve the pipeline
    # meaning only when the task did not name a more specific boundary.
    if any(token in {"processor", "processors", "router", "routing"} for token in tokens):
        return "processor"
    return next((COMPONENT_ALIASES[token] for token in reversed(tokens) if token in COMPONENT_ALIASES), None)


def _subsystem(text: str) -> str | None:
    """Return only a subsystem explicitly adjacent to a component phrase."""
    component_words = "|".join(
        sorted((re.escape(word) for word in COMPONENT_ALIASES), key=len, reverse=True)
    )
    matches = list(
        re.finditer(
            rf"\b(?P<subsystem>[A-Za-z][A-Za-z0-9_-]*)\s+(?:{component_words})\b",
            text,
            re.IGNORECASE,
        )
    )
    ignored = (
        set(COMPONENT_ALIASES)
        | set(ROLE_WORDS)
        | set(INTENT_WORDS)
        | set(GENERIC_ROOTS)
        | {"application", "domain", "infrastructure", "boundary", "persistence", "layer",
           "responsible", "source", "implementation", "current"}
    )
    for match in reversed(matches):
        token = match.group("subsystem").casefold()
        if token not in ignored and len(token) > 2:
            return token
    return None


def _contrastive_spans(task: str) -> tuple[list[str], str]:
    """Exclude contrastive clauses, but retain ordinary behavioral negation."""
    excluded: list[str] = []
    positive_parts: list[str] = []
    cursor = 0
    for match in NEGATIVE_PATTERN.finditer(task):
        prefix = task[cursor:match.start()]
        before = task[:match.start()]
        # "is not normalized" describes faulty behavior; it is not a candidate exclusion.
        if re.search(r"\b(?:am|are|is|was|were|be|been|being|do|does|did)\s*$", before, re.I):
            continue
        positive_parts.append(prefix)
        excluded.append(match.group("value"))
        cursor = match.end()
    positive_parts.append(task[cursor:])
    return excluded, " ".join(positive_parts)


def parse_task_query(task: str) -> TaskQuery:
    """Parse positive and contrastive task intent without fixture knowledge."""
    excluded_spans, positive_text = _contrastive_spans(task)
    positive_tokens = _tokens(positive_text)
    request_parts = re.split(
        r"\b(?:find|locate|identify|determine)\b",
        positive_text,
        flags=re.IGNORECASE,
    )
    request_text = request_parts[-1] if len(request_parts) > 1 else positive_text
    requested_component = _component(_tokens(request_text))
    # Admission language names a boundary even when a task uses the operation
    # rather than its implementation noun (for example, a receiver admitting
    # an incoming message).  This is deliberately architecture-level rather
    # than repository- or protocol-specific.
    if requested_component is None and re.search(
        r"\b(?:incoming|ingress|admission|admit(?:s|ted|ting)?|enters?)\b",
        positive_text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(?:message|messages|signal|signals|event|events|request|requests|payload)\b",
        positive_text,
        re.IGNORECASE,
    ):
        requested_component = "receiver"
    if re.search(r"\b(?:accept(?:ed|s)?|eligible|match(?:es|ed)?|permit(?:s|ted)?|satisf(?:y|ies|ied))\b", positive_text, re.I):
        positive_tokens.extend(("bool", "match"))
    present = set(positive_tokens)
    for group in CONCEPT_GROUPS:
        if present & group:
            positive_tokens.extend(group - present)
    intents = {
        intent for token in positive_tokens if (intent := INTENT_WORDS.get(token))
    } or {"ownership"}
    if re.search(
        r"\b(?:if|when)\b.{0,100}\bchanges?\b|\bmust\s+change\s+together\b|"
        r"\b(?:affected|impacted)\b",
        positive_text,
        re.IGNORECASE,
    ):
        intents.add("impact")
    architectural_words = (
        set(COMPONENT_ALIASES)
        | set(INTENT_WORDS)
        | set(ROLE_WORDS)
        | {"application", "boundary", "domain", "infrastructure", "layer", "persistence", "plugin"}
    )
    positive_tokens = [token for token in positive_tokens if token not in architectural_words]
    if present & {"job", "jobs", "worker", "workers"} and requested_component != "job":
        positive_tokens.append("job")
    excluded_tokens = [token for span in excluded_spans for token in _tokens(span)]
    excluded_tokens = [token for token in excluded_tokens if token not in set(positive_tokens)]

    excluded_components = frozenset(
        component
        for token in excluded_tokens
        if (component := COMPONENT_ALIASES.get(token))
    )
    if requested_component in excluded_components:
        excluded_components = excluded_components - {requested_component}
    lowered = task.casefold()
    requested_layer = next(
        (
            layer
            for layer in ("domain", "application", "infrastructure", "boundary", "persistence")
            if re.search(
                rf"\b{layer}(?:-layer|\s+layer)\b"
                if layer == "boundary"
                else rf"\b{layer}(?:-layer|\s+layer)?\b",
                lowered,
            )
        ),
        None,
    )
    if requested_layer is None and requested_component in {"adapter", "repository"}:
        requested_layer = "persistence"
    if requested_component is None and {"eligibility", "bounded", "bound"} & set(positive_tokens):
        requested_component = "policy"
    positive_subsystem = _subsystem(request_text)
    negative_candidate = next(
        (value for span in excluded_spans if (value := _subsystem(span))),
        None,
    )
    if not positive_subsystem and requested_layer and negative_candidate and excluded_components:
        positive_subsystem = negative_candidate
        negative_subsystem = None
        promoted = set(_tokens(negative_candidate))
        excluded_tokens = [token for token in excluded_tokens if token not in promoted]
    else:
        negative_subsystem = negative_candidate if positive_subsystem else None
    excluded_roles = frozenset(ROLE_WORDS[token] for token in excluded_tokens if token in ROLE_WORDS)

    for token in excluded_tokens:
        excluded_intent = INTENT_WORDS.get(token)
        if excluded_intent:
            intents.discard(excluded_intent)
    if not intents:
        intents.add("ownership")

    multi = bool(re.search(r"\b(?:co-?owners?|multiple owners?|all owners?|both owners?|owner set)\b", lowered))
    cardinality: OwnerCardinality = "multi" if multi else "single"
    return TaskQuery(
        positive_concepts=frozenset(positive_tokens),
        excluded_concepts=frozenset(excluded_tokens),
        requested_subsystem=positive_subsystem,
        excluded_subsystem=negative_subsystem,
        requested_component_type=requested_component,
        excluded_component_types=excluded_components,
        requested_layer=requested_layer,
        intents=frozenset(intents),
        owner_cardinality=cardinality,
        excluded_roles=excluded_roles,
    )
