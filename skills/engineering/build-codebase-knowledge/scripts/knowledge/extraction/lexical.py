"""Lexical symbol and import extractor for Go, Rust, Java, C, and C++."""

from __future__ import annotations

import re
from pathlib import Path

from knowledge.extraction.base import ExtractedSymbol


def extract_lexical_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract Go/Rust/Java/C/C++ symbols and imports line-by-line.
    
    Returns:
        (symbols, imports, confidence, unknowns)
    """
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []
    unknowns: list[str] = []
    confidence = "medium"

    stem = Path(rel_str).stem
    lines = content.splitlines()

    # Generic symbol patterns for Go/Rust/Java/C/C++
    sym_pat = re.compile(
        r"^\s*(?:pub\s+)?(?:public\s+|private\s+|protected\s+)?(?:fn|func|type|struct|enum|class|trait|impl|void|int|char|double|float)\s+([a-zA-Z0-9_]+)"
    )
    import_pat = re.compile(r"^\s*(?:import|include|use)\s+['\"]?([a-zA-Z0-9_/\.-]+)['\"]?")

    for line_idx, line in enumerate(lines, start=1):
        line_str = line.strip()

        m_imp = import_pat.search(line_str)
        if m_imp:
            imports.append(m_imp.group(1))

        m_sym = sym_pat.search(line_str)
        if m_sym:
            name = m_sym.group(1)
            symbols.append(
                ExtractedSymbol(
                    name=name,
                    qualified_name=f"{stem}.{name}",
                    kind="symbol",
                    path=rel_str,
                    line_start=line_idx,
                    line_end=line_idx,
                    subsystem=subsystem,
                    docstring="",
                )
            )

    return sorted(symbols, key=lambda s: (s.line_start, s.name)), sorted(list(set(imports))), confidence, unknowns
