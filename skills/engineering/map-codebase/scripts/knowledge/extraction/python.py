"""AST-based symbol and import extractor for Python."""

from __future__ import annotations

import ast
from pathlib import Path

from knowledge.extraction.base import ExtractedSymbol, SymbolEvidence, infer_component_types


def _render(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _symbol_evidence(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> SymbolEvidence:
    decorators = [_render(item) for item in node.decorator_list]
    decorators = [item for item in decorators if item]
    interfaces = [_render(item) for item in node.bases] if isinstance(node, ast.ClassDef) else []
    type_hints: list[str] = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        if node.args.vararg:
            arguments.append(node.args.vararg)
        if node.args.kwarg:
            arguments.append(node.args.kwarg)
        type_hints = [_render(item.annotation) for item in arguments if item.annotation]
        if node.returns:
            type_hints.append(_render(node.returns))
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        signature = f"{prefix} {node.name}({_render(node.args)})"
        if node.returns:
            signature += f" -> {_render(node.returns)}"
    else:
        signature = f"class {node.name}"
        if interfaces:
            signature += f"({', '.join(interfaces)})"

    calls = sorted(
        {
            value
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and (value := _call_name(child.func))
        }
    )
    references = sorted(
        {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name)
            and (child.id.isupper() or any(token in child.id.lower() for token in ("config", "setting", "env")))
        }
    )
    flow_kinds = (
        (ast.Raise, "raises"),
        (ast.Try, "try"),
        (ast.If, "conditional"),
        ((ast.For, ast.AsyncFor, ast.While), "loop"),
        ((ast.With, ast.AsyncWith), "context-manager"),
        ((ast.Yield, ast.YieldFrom), "generator"),
    )
    control_flow = sorted(
        {
            label
            for child in ast.walk(node)
            for node_type, label in flow_kinds
            if isinstance(child, node_type)
        }
    )
    return {
        "signature": signature,
        "type_hints": sorted(set(filter(None, type_hints))),
        "decorators": decorators,
        "interfaces": sorted(set(filter(None, interfaces))),
        "references": references,
        "control_flow": control_flow,
        "calls": calls,
    }


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
                evidence = _symbol_evidence(node)

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
                        component_types=infer_component_types(
                            rel_str,
                            name=name,
                            decorators=evidence["decorators"],
                            imports=imports,
                            content=ast.get_source_segment(content, node) or "",
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
