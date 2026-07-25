"""Lexical symbol and import extractor for JavaScript, TypeScript, JSX, and TSX."""

from __future__ import annotations

import re
from pathlib import Path

from knowledge.extraction.base import ExtractedSymbol


def extract_javascript_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract JS/TS symbols and imports line-by-line.

    Returns:
        (symbols, imports, confidence, unknowns)
    """
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []
    unknowns: list[str] = []
    confidence = "medium"

    stem = Path(rel_str).stem
    lines = content.splitlines()

    # Pattern for imports: import ... from 'path' or require('path')
    import_pat = re.compile(r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))")

    # Pattern for exported or top-level declarations
    decl_pat = re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class|interface|type|const|let|var)\s+([a-zA-Z0-9_]+)"
    )

    for line_idx, line in enumerate(lines, start=1):
        line_str = line.strip()

        # Check imports
        for match in import_pat.finditer(line_str):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.append(imp)

        # Check symbol declarations
        m_decl = decl_pat.search(line_str)
        if m_decl:
            name = m_decl.group(1)
            kind = "class" if "class" in line_str or "interface" in line_str else "function"
            symbols.append(
                ExtractedSymbol(
                    name=name,
                    qualified_name=f"{stem}.{name}",
                    kind=kind,
                    path=rel_str,
                    line_start=line_idx,
                    line_end=line_idx,
                    subsystem=subsystem,
                    docstring="",
                )
            )

    return sorted(symbols, key=lambda s: (s.line_start, s.name)), sorted(list(set(imports))), confidence, unknowns
