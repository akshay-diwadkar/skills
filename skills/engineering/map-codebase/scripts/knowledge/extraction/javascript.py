"""Tree-sitter symbol and import extraction for JavaScript, TypeScript, JSX, and TSX."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from knowledge.extraction.base import ExtractedSymbol

GRAMMARS = {
    ".js": "tree_sitter_javascript",
    ".jsx": "tree_sitter_javascript",
    ".ts": "tree_sitter_typescript",
    ".tsx": "tree_sitter_typescript",
}

# TypeScript module exposes `language_typescript` and `language_tsx`
TS_LANGUAGE_FUNCS = {
    ".ts": "language_typescript",
    ".tsx": "language_tsx",
}

DECLARATIONS = {
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "class_declaration": "class",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "enum_declaration": "enum",
    "lexical_declaration": "variable",
    "variable_declaration": "variable",
    "method_definition": "method",
}

IMPORT_NODES = {
    "import_statement",
    "import_declaration",  # tree-sitter-typescript uses this
}

IDENTIFIER_TYPES = {"identifier", "property_identifier", "type_identifier"}


def _load_parser(suffix: str) -> Any:
    """Load one required grammar and return a version-compatible Parser."""
    module_name = GRAMMARS[suffix]
    try:
        grammar = importlib.import_module(module_name)
        tree_sitter = importlib.import_module("tree_sitter")
    except ImportError as exc:
        raise RuntimeError(
            f"Tree-sitter grammar '{module_name}' is required for {suffix} extraction; "
            "install skills/engineering/map-codebase/requirements.txt"
        ) from exc

    if suffix in TS_LANGUAGE_FUNCS:
        language_factory = getattr(grammar, TS_LANGUAGE_FUNCS[suffix], None)
    else:
        language_factory = getattr(grammar, "language", None)
    if language_factory is None:
        raise RuntimeError(f"Tree-sitter grammar '{module_name}' does not expose language()")
    raw_language = language_factory()
    try:
        language = tree_sitter.Language(raw_language)
    except TypeError:
        language = raw_language
    try:
        return tree_sitter.Parser(language)
    except TypeError:
        parser = tree_sitter.Parser()
        if hasattr(parser, "set_language"):
            parser.set_language(language)
        else:
            parser.language = language
        return parser


def _text(node: Any, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _first_identifier(node: Any) -> Any | None:
    if node.type in IDENTIFIER_TYPES:
        return node
    for child in node.named_children:
        found = _first_identifier(child)
        if found is not None:
            return found
    return None


def _extract_import_source(node: Any, source: bytes) -> str | None:
    """Extract the module path string from an import node."""
    src = node.child_by_field_name("source")
    if src is not None:
        return _text(src, source).strip("'\"")
    # Fallback: find string child
    for child in node.named_children:
        if child.type == "string":
            return _text(child, source).strip("'\"")
    return None


def _declaration_name(node: Any, source: bytes) -> str | None:
    """Extract the declared name from a declaration node."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node, source)
    # For variable declarations, look inside declarators
    for child in node.named_children:
        if child.type in ("variable_declarator", "lexical_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                return _text(name_node, source)
    found = _first_identifier(node)
    return _text(found, source) if found is not None else None


def extract_javascript_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract JS/TS symbols and imports using tree-sitter AST.

    Returns:
        (symbols, imports, confidence, unknowns)
    """
    suffix = full_path.suffix.lower()
    if suffix not in GRAMMARS:
        return [], [], "low", [f"unsupported JS/TS suffix: {suffix}"]

    source = content.encode("utf-8")
    tree = _load_parser(suffix).parse(source)
    stem = Path(rel_str).stem
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []

    def visit(node: Any, scope: tuple[str, ...] = ()) -> None:
        # Handle imports
        if node.type in IMPORT_NODES:
            imp = _extract_import_source(node, source)
            if imp:
                imports.append(imp)
            return  # Don't recurse into import internals

        # Handle require() calls
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func is not None and _text(func, source) == "require":
                args = node.child_by_field_name("arguments")
                if args is not None:
                    for child in args.named_children:
                        if child.type == "string":
                            imports.append(_text(child, source).strip("'\""))

        # Handle export statements that wrap declarations
        if node.type in ("export_statement", "export_declaration"):
            for child in node.named_children:
                if child.type in DECLARATIONS:
                    visit(child, scope)
            return

        # Handle declarations
        kind = DECLARATIONS.get(node.type)
        if kind is not None:
            name = _declaration_name(node, source)
            if name and name not in ("const", "let", "var", "async", "function", "class"):
                qualified = ".".join((stem, *scope, name))
                symbols.append(
                    ExtractedSymbol(
                        name=name,
                        qualified_name=qualified,
                        kind=kind,
                        path=rel_str,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        subsystem=subsystem,
                        docstring="",
                    )
                )
                # Use this declaration as a scope for children (classes, etc.)
                if node.type == "class_declaration":
                    for child in node.named_children:
                        visit(child, (*scope, name))
                    return

        # Recurse into children
        for child in node.named_children:
            visit(child, scope)

    visit(tree.root_node)
    unknowns = ["tree-sitter parse contained syntax errors"] if tree.root_node.has_error else []
    confidence = "medium" if unknowns else "high"

    seen_keys: set[tuple[str, str, int]] = set()
    deduped_symbols: list[ExtractedSymbol] = []
    for s in sorted(symbols, key=lambda item: (item.line_start, item.qualified_name)):
        key = (s.path, s.name, s.line_start)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_symbols.append(s)

    return (
        deduped_symbols,
        sorted(set(imports)),
        confidence,
        unknowns,
    )
