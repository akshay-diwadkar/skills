"""Rank symbols before aggregating ownership to files."""

from __future__ import annotations

import re
from typing import Any

from resolver.features import tokenize
from resolver.ranking_utils import capped_sum
from resolver.schemas import TaskQuery


def _distinct_matches(tokens: set[str] | frozenset[str]) -> tuple[set[str] | frozenset[str], int]:
    """Collapse light morphology variants so one word cannot exhaust a family cap."""
    roots = {token[:5] if len(token) > 5 else token for token in tokens}
    return tokens, len(roots)


def symbol_score(symbol: dict[str, Any], query: TaskQuery) -> tuple[float, list[str]]:
    name = str(symbol.get("name", ""))
    exact = (
        name.casefold() in query.positive_concepts
        and ("_" in name or len(name) >= 7)
    )
    fields = {
        "name": tokenize(name) | tokenize(str(symbol.get("qualified_name", ""))),
        "signature": tokenize(str(symbol.get("signature", ""))),
        "docstring": tokenize(str(symbol.get("docstring", ""))),
        "decorator": tokenize(" ".join(symbol.get("decorators", []))),
        "interface": tokenize(" ".join(symbol.get("interfaces", []))),
        "reference": tokenize(" ".join(symbol.get("references", []))),
        "control_flow": tokenize(" ".join(symbol.get("control_flow", []))),
    }
    weights = {
        "name": 8.0,
        "signature": 6.0,
        "docstring": 4.0,
        "decorator": 5.0,
        "interface": 5.0,
        "reference": 2.5,
        "control_flow": 2.0,
    }
    evidence: list[str] = []
    contributions = []
    if exact:
        contributions.append(30.0)
        evidence.append(f"exact_symbol: {name}")
    for family, tokens in fields.items():
        matched = query.positive_concepts & tokens
        if matched:
            _, distinct_count = _distinct_matches(matched)
            contributions.append(weights[family] * min(3, distinct_count))
            evidence.append(f"symbol_{family}: {','.join(sorted(matched)[:3])}")
    signature = str(symbol.get("signature", ""))
    if "bool" in query.positive_concepts and re.search(r"->\s*bool\b", signature):
        contributions.append(18.0)
        evidence.append("symbol_return_type: bool")
    conflicts = query.excluded_concepts & set().union(*fields.values())
    score = capped_sum(contributions, 60.0) - min(30.0, 10.0 * len(conflicts))
    if conflicts:
        evidence.append(f"negative_symbol_conflict: {','.join(sorted(conflicts)[:3])}")
    return score, evidence


def rank_symbols(symbols: list[dict[str, Any]], query: TaskQuery) -> list[tuple[dict[str, Any], float, list[str]]]:
    ranked = [
        (symbol, *symbol_score(symbol, query))
        for symbol in symbols
    ]
    return sorted(
        (item for item in ranked if item[1] > 0),
        key=lambda item: (-item[1], int(item[0].get("line_start", 0)), str(item[0].get("qualified_name", ""))),
    )
