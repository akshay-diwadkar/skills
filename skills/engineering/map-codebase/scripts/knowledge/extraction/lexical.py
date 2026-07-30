"""Tree-sitter symbol and import extraction for Go, Rust, Java, C, and C++."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from knowledge.extraction.base import ExtractedSymbol, SymbolEvidence, infer_component_types

GRAMMARS = {
    ".go": "tree_sitter_go",
    ".rs": "tree_sitter_rust",
    ".java": "tree_sitter_java",
    ".c": "tree_sitter_c",
    ".cpp": "tree_sitter_cpp",
}

DECLARATIONS: dict[str, dict[str, str]] = {
    ".go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_spec": "type",
    },
    ".rs": {
        "function_item": "function",
        "struct_item": "struct",
        "enum_item": "enum",
        "trait_item": "trait",
        "type_item": "type",
        "union_item": "union",
        "impl_item": "impl",
    },
    ".java": {
        "class_declaration": "class",
        "interface_declaration": "interface",
        "enum_declaration": "enum",
        "record_declaration": "record",
        "method_declaration": "method",
        "constructor_declaration": "constructor",
    },
    ".c": {
        "function_definition": "function",
        "struct_specifier": "struct",
        "enum_specifier": "enum",
        "type_definition": "type",
    },
    ".cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "struct",
        "enum_specifier": "enum",
        "namespace_definition": "namespace",
        "type_definition": "type",
    },
}

SCOPES = {
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "record_declaration",
    "struct_item",
    "enum_item",
    "trait_item",
    "impl_item",
    "class_specifier",
    "struct_specifier",
    "namespace_definition",
}

IDENTIFIER_TYPES = {
    "identifier",
    "field_identifier",
    "type_identifier",
    "namespace_identifier",
}


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


def _declaration_name(node: Any, source: bytes) -> str | None:
    direct = node.child_by_field_name("name")
    if direct is not None:
        return _text(direct, source)
    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        found = _first_identifier(declarator)
        if found is not None:
            return _text(found, source)
    if node.type == "impl_item":
        target = node.child_by_field_name("type")
        if target is not None:
            return _text(target, source)
    found = _first_identifier(node)
    return _text(found, source) if found is not None else None


def _normalize_import(node: Any, source: bytes, suffix: str) -> str | None:
    value = _text(node, source).strip()
    if suffix == ".go":
        path = node.child_by_field_name("path")
        value = _text(path, source) if path is not None else value
        return value.strip("\"'`")
    if suffix == ".rs":
        value = value.removeprefix("use").removesuffix(";").strip()
        return value.replace("::", "/")
    if suffix == ".java":
        value = value.removeprefix("import").removeprefix("static").removesuffix(";").strip()
        return value.replace(".", "/")
    path = node.child_by_field_name("path")
    if path is not None:
        value = _text(path, source)
    return value.strip("<>\"'")


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
    calls = set()
    for child in descendants:
        if child.type in {"call_expression", "method_invocation"}:
            function = (
                child.child_by_field_name("function")
                or child.child_by_field_name("name")
                or child.child_by_field_name("method")
            )
            if function is not None:
                calls.add(_text(function, source))
    flow_map = {
        "throw_statement": "raises",
        "raise_expression": "raises",
        "try_statement": "try",
        "if_statement": "conditional",
        "if_expression": "conditional",
        "match_expression": "conditional",
        "switch_statement": "conditional",
        "for_statement": "loop",
        "for_expression": "loop",
        "while_statement": "loop",
        "while_expression": "loop",
        "yield_expression": "generator",
    }
    decorators = [
        _text(child, source).lstrip("@#[").rstrip("]")
        for child in node.named_children
        if child.type in {"annotation", "attribute_item", "attribute"}
    ]
    interfaces = [
        _text(child, source)
        for child in node.named_children
        if child.type in {
            "superclass",
            "super_interfaces",
            "extends_interfaces",
            "trait_bounds",
            "base_class_clause",
        }
    ]
    return {
        "signature": signature,
        "type_hints": [],
        "decorators": decorators,
        "interfaces": interfaces,
        "references": sorted(
            {
                _text(child, source)
                for child in descendants
                if child.type in IDENTIFIER_TYPES
                and (
                    _text(child, source).isupper()
                    or any(token in _text(child, source).lower() for token in ("config", "setting", "env"))
                )
            }
        ),
        "control_flow": sorted({flow_map[child.type] for child in descendants if child.type in flow_map}),
        "calls": sorted(calls),
    }


def extract_lexical_file(
    full_path: Path,
    rel_str: str,
    content: str,
    subsystem: str,
) -> tuple[list[ExtractedSymbol], list[str], str, list[str]]:
    """Extract scope-aware symbols and imports with the required tree-sitter grammar."""
    suffix = full_path.suffix.lower()
    if suffix not in GRAMMARS:
        raise ValueError(f"Unsupported tree-sitter extraction suffix: {suffix}")
    source = content.encode("utf-8")
    tree = _load_parser(suffix).parse(source)
    stem = Path(rel_str).stem
    symbols: list[ExtractedSymbol] = []
    imports: list[str] = []
    import_nodes = {
        ".go": {"import_spec"},
        ".rs": {"use_declaration"},
        ".java": {"import_declaration"},
        ".c": {"preproc_include"},
        ".cpp": {"preproc_include"},
    }[suffix]

    def visit(node: Any, scope: tuple[str, ...]) -> None:
        if node.type in import_nodes:
            imported = _normalize_import(node, source, suffix)
            if imported:
                imports.append(imported)

        name = None
        kind = DECLARATIONS[suffix].get(node.type)
        if kind is not None:
            name = _declaration_name(node, source)
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

        child_scope = (*scope, name) if name and node.type in SCOPES else scope
        for child in node.named_children:
            visit(child, child_scope)

    visit(tree.root_node, ())
    unknowns = ["tree-sitter parse contained syntax errors"] if tree.root_node.has_error else []
    confidence = "medium" if unknowns else "high"
    return (
        sorted(symbols, key=lambda item: (item.line_start, item.qualified_name)),
        sorted(set(imports)),
        confidence,
        unknowns,
    )
