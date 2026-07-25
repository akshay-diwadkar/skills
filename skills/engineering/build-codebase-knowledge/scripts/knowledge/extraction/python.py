"""AST-based symbol and import extractor for Python."""

from __future__ import annotations

import ast
from pathlib import Path

from knowledge.extraction.base import ExtractedSymbol


def extract_python_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract Python symbols and imports using Python's builtin ast module.

    Returns:
        (symbols, imports, confidence, unknowns)
    """
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []
    unknowns: list[str] = []
    confidence = "high"

    try:
        tree = ast.parse(content, filename=str(full_path))
        stem = Path(rel_str).stem

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                kind = (
                    "class"
                    if isinstance(node, ast.ClassDef)
                    else ("async-function" if isinstance(node, ast.AsyncFunctionDef) else "function")
                )
                docstring = ast.get_docstring(node) or ""
                docstring_summary = docstring.splitlines()[0] if docstring else ""

                symbols.append(
                    ExtractedSymbol(
                        name=name,
                        qualified_name=f"{stem}.{name}",
                        kind=kind,
                        path=rel_str,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        subsystem=subsystem,
                        docstring=docstring_summary,
                    )
                )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

    except SyntaxError as exc:
        confidence = "low"
        unknowns.append(f"Python syntax error at line {exc.lineno}: {exc.msg}")
    except Exception as exc:
        confidence = "low"
        unknowns.append(f"AST parsing exception: {exc}")

    return sorted(symbols, key=lambda s: (s.line_start, s.name)), sorted(list(set(imports))), confidence, unknowns
