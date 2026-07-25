"""Stage A: Multi-signal extraction engine."""

from __future__ import annotations

import re
from typing import Any


def split_identifier(ident: str) -> list[str]:
    """Split identifier into sub-words based on camelCase, PascalCase, snake_case, kebab-case."""
    # Replace separators
    s = ident.replace("_", " ").replace("-", " ").replace(".", " ")
    # Insert space before capital letters
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return [w.lower() for w in s.split() if len(w) > 1]


def extract_signals(task: str, index_data: dict[str, Any]) -> dict[str, Any]:
    """Extract precise task signals from natural language task description."""
    # Quoted terms
    quoted_terms = re.findall(r"['\"]([^'\"]+)['\"]", task)

    # File paths & extensions
    paths = re.findall(r"[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_]+", task)

    # Identifiers
    raw_idents = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_\-\.]*\b", task)
    split_words: set[str] = set()

    for idf in raw_idents:
        for word in split_identifier(idf):
            split_words.add(word)

    # Repository-derived vocabulary
    repo_subsystems = {s["name"].lower() for s in index_data.get("subsystems", [])}
    repo_symbols = {s["name"].lower() for s in index_data.get("symbols", [])}

    matched_subsystems = [sub for sub in repo_subsystems if sub in task.lower()]
    matched_symbols = [sym for sym in repo_symbols if sym in task.lower()]

    # Action verbs
    action_verbs = re.findall(
        r"(?i)\b(add|create|update|fix|refactor|remove|delete|optimize|test|configure|migrate|clean|debug)\b",
        task,
    )

    return {
        "raw_task": task,
        "quoted_terms": sorted(list(set(quoted_terms))),
        "paths": sorted(list(set(paths))),
        "raw_identifiers": sorted(list(set(raw_idents))),
        "split_words": sorted(list(split_words)),
        "subsystems": sorted(matched_subsystems),
        "symbols": sorted(matched_symbols),
        "action_verbs": sorted(list(set([a.lower() for a in action_verbs]))),
    }
