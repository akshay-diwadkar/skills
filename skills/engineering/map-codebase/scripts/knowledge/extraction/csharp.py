"""Tree-sitter symbol and import extraction for C#."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from knowledge.extraction.base import ExtractedSymbol, SymbolEvidence, infer_component_types

DECLARATIONS = {
    "class_declaration": "class",
    "struct_declaration": "struct",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "record_declaration": "record",
    "method_declaration": "method",
    "constructor_declaration": "constructor",
    "delegate_declaration": "delegate",
    "namespace_declaration": "namespace",
}

IDENTIFIER_TYPES = {"identifier", "name"}
SCOPES = {"class_declaration", "struct_declaration", "interface_declaration", "namespace_declaration"}


def _load_parser(suffix: str) -> Any:
    """Load the C# tree-sitter grammar."""
    try:
        grammar = importlib.import_module("tree_sitter_c_sharp")
        tree_sitter = importlib.import_module("tree_sitter")
    except ImportError as exc:
        raise RuntimeError(
            "Tree-sitter grammar 'tree_sitter_c_sharp' is required for .cs extraction; "
            "install tree-sitter-c-sharp"
        ) from exc
    language_factory = getattr(grammar, "language", None)
    if language_factory is None:
        raise RuntimeError("tree_sitter_c_sharp does not expose language()")
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


def _descendants(node: Any) -> list[Any]:
    result: list[Any] = []
    pending = list(node.named_children)
    while pending:
        child = pending.pop()
        result.append(child)
        pending.extend(child.named_children)
    return result


def _symbol_evidence(node: Any, source: bytes) -> SymbolEvidence:
    descendants = _descendants(node)
    raw = _text(node, source)
    signature = raw.split("{", 1)[0].strip().rstrip(";")[:500]
    decorators = [
        _text(child, source).strip("[]")
        for child in node.named_children
        if child.type in {"attribute_list", "attribute"}
    ]
    interfaces = [
        _text(child, source).lstrip(":").strip()
        for child in node.named_children
        if child.type in {"base_list", "base_type"}
    ]
    calls = set()
    for child in descendants:
        if child.type == "invocation_expression":
            function = child.child_by_field_name("function")
            if function is not None:
                calls.add(_text(function, source))
    flow_map = {
        "throw_statement": "raises",
        "try_statement": "try",
        "if_statement": "conditional",
        "switch_statement": "conditional",
        "for_statement": "loop",
        "foreach_statement": "loop",
        "while_statement": "loop",
        "yield_statement": "generator",
        "using_statement": "context-manager",
    }
    return {
        "signature": signature,
        "type_hints": [],
        "decorators": decorators,
        "interfaces": interfaces,
        "references": sorted(
            {
                _text(child, source)
                for child in descendants
                if child.type == "identifier"
                and (
                    _text(child, source).isupper()
                    or any(token in _text(child, source).lower() for token in ("config", "setting", "env"))
                )
            }
        ),
        "control_flow": sorted({flow_map[child.type] for child in descendants if child.type in flow_map}),
        "calls": sorted(calls),
    }


def extract_csharp_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract C# symbols and imports using tree-sitter."""
    source = content.encode("utf-8")
    tree = _load_parser(".cs").parse(source)
    stem = Path(rel_str).stem
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []

    def visit(node: Any, scope: tuple[str, ...] = ()) -> None:
        # Handle using directives
        if node.type == "using_directive":
            name = node.child_by_field_name("name")
            if name is None:
                name = _first_identifier(node)
            if name is not None:
                imports.append(_text(name, source))
            return

        kind = DECLARATIONS.get(node.type)
        if kind is not None:
            name_node = node.child_by_field_name("name")
            name = _text(name_node, source) if name_node else None
            if not name:
                found = _first_identifier(node)
                name = _text(found, source) if found else None
            if name:
                qualified = ".".join((stem, *scope, name))
                evidence = _symbol_evidence(node, source)
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
                        component_types=infer_component_types(
                            rel_str,
                            name=name,
                            decorators=evidence["decorators"],
                            imports=imports,
                            content=_text(node, source),
                        ),
                        signature=str(evidence["signature"]),
                        type_hints=list(evidence["type_hints"]),
                        decorators=list(evidence["decorators"]),
                        interfaces=list(evidence["interfaces"]),
                        references=list(evidence["references"]),
                        control_flow=list(evidence["control_flow"]),
                        calls=list(evidence["calls"]),
                    )
                )
                if node.type in SCOPES:
                    for child in node.named_children:
                        visit(child, (*scope, name))
                    return

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
