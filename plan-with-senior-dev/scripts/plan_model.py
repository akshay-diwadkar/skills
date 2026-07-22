"""Structured Markdown model and repository-grounded checks for v3 plans."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from _plan_utils import Diagnostic, strip_fenced_code_blocks, validate_receipt
from plan_contract import load_contract


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})([A-Za-z0-9_-]*)\s*$")
CITATION_RE = re.compile(r"`(?P<path>(?:[A-Za-z]:[\\/])?[^`\r\n]+):(?P<line>\d+)`")
ID_RE = re.compile(r"\b(?P<id>(?:SC|F|D|CH|T|C|R)-[1-9]\d*)\b")
ID_DEF_RE = re.compile(r"\b(?P<id>(?:SC|F|D|CH|T|C|R)-[1-9]\d*)(?:\s+P[012])?\s*:")
FACT_RE = re.compile(
    r"^- (?P<id>F-[1-9]\d*):\s+`(?P<path>(?:[A-Za-z]:[\\/])?[^`\r\n]+):(?P<line>\d+)`"
    r"\s+\|\s+anchor:\s+`(?P<anchor>[^`\r\n]+)`\s+\|\s+observation:\s+(?P<observation>.+)$",
    re.MULTILINE,
)
CHANGE_RE = re.compile(
    r"^- (?P<id>CH-[1-9]\d*):\s+`(?P<path>[^`\r\n]+)`\s+\|\s+anchor:\s+`(?P<anchor>[^`\r\n]+)`"
    r"\s+\|\s+status:\s+(?P<status>existing|new)\s+\|\s+change:\s+(?P<change>.+)$",
    re.MULTILINE | re.IGNORECASE,
)
BLUEPRINT_HEADING_RE = re.compile(
    r"^Execution Blueprint:\s+(?P<ids>CH-[1-9]\d*(?:\s*,\s*CH-[1-9]\d*)*)\s+[—-]\s+(?P<purpose>\S.+)$"
)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


@dataclass(frozen=True)
class CodeBlock:
    language: str
    body: str
    start_line: int
    end_line: int | None


@dataclass(frozen=True)
class Section:
    name: str
    level: int
    line: int
    body: str

    @property
    def has_content(self) -> bool:
        return bool(self.body.strip())

    @property
    def end_line(self) -> int:
        return self.line + len(self.body.splitlines())


@dataclass(frozen=True)
class ExecutionBlueprint:
    change_ids: tuple[str, ...]
    purpose: str
    line: int
    kinds: tuple[str, ...]

    @property
    def has_artifact(self) -> bool:
        return bool(self.kinds)


@dataclass(frozen=True)
class MarkdownDocument:
    text: str
    sections: tuple[Section, ...]
    code_blocks: tuple[CodeBlock, ...]
    diagnostics: tuple[Diagnostic, ...]

    def find_section(self, name: str) -> Section | None:
        return next((item for item in self.sections if item.name == name), None)

    @property
    def prose_text(self) -> str:
        return strip_fenced_code_blocks(self.text)


def parse_markdown(text: str) -> MarkdownDocument:
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []
    blocks: list[CodeBlock] = []
    diagnostics: list[Diagnostic] = []
    fence_character: str | None = None
    fence_length = 0
    fence_language = ""
    fence_start = 0
    fence_body_start = 0

    for index, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
                fence_language = fence.group(2).casefold()
                fence_start = index
                fence_body_start = index + 1
            elif marker[0] == fence_character and len(marker) >= fence_length:
                body = "\n".join(lines[fence_body_start - 1:index - 1])
                blocks.append(CodeBlock(fence_language, body, fence_start, index))
                fence_character = None
            continue

        if fence_character is None:
            heading = HEADING_RE.match(line)
            if heading:
                headings.append((index, len(heading.group(1)), heading.group(2).strip()))

    if fence_character is not None:
        blocks.append(CodeBlock(fence_language, "\n".join(lines[fence_body_start - 1:]), fence_start, None))
        diagnostics.append(Diagnostic("markdown.fence.unclosed", "Fenced code block is not closed", fence_start))

    sections: list[Section] = []
    for position, (line_number, level, name) in enumerate(headings):
        next_line = len(lines) + 1
        for candidate_line, candidate_level, _ in headings[position + 1:]:
            if candidate_level <= level:
                next_line = candidate_line
                break
        body = "\n".join(lines[line_number:next_line - 1])
        sections.append(Section(name, level, line_number, body))

    return MarkdownDocument(text, tuple(sections), tuple(blocks), tuple(diagnostics))


def definitions(text: str, kind: str | None = None) -> set[str]:
    values = {match.group("id") for match in ID_DEF_RE.finditer(strip_fenced_code_blocks(text))}
    if kind is None:
        return values
    return {value for value in values if value.startswith(f"{kind}-")}


def _line_for(text: str, needle: str) -> int | None:
    return next((index for index, line in enumerate(text.splitlines(), start=1) if needle in line), None)


def _has_markdown_table(body: str) -> bool:
    lines = body.splitlines()
    return any(
        "|" in lines[index] and TABLE_SEPARATOR_RE.match(lines[index + 1])
        for index in range(len(lines) - 1)
    )


def execution_blueprints(document: MarkdownDocument) -> tuple[ExecutionBlueprint, ...]:
    implementation = document.find_section("Implementation Specification")
    if implementation is None:
        return ()
    blueprints: list[ExecutionBlueprint] = []
    for section in document.sections:
        if section.level != 3 or not (implementation.line < section.line <= implementation.end_line):
            continue
        match = BLUEPRINT_HEADING_RE.fullmatch(section.name)
        if match is None:
            continue
        kinds: list[str] = []
        for block in document.code_blocks:
            if block.end_line is None or not (section.line < block.start_line <= section.end_line):
                continue
            if not block.body.strip():
                continue
            if block.language == "pseudocode":
                kinds.append("pseudocode")
            elif block.language == "mermaid":
                kinds.append("mermaid")
            else:
                kinds.append("code")
        if _has_markdown_table(section.body):
            kinds.append("table")
        blueprints.append(ExecutionBlueprint(
            tuple(item.strip() for item in match.group("ids").split(",")),
            match.group("purpose"),
            section.line,
            tuple(dict.fromkeys(kinds)),
        ))
    return tuple(blueprints)


def _resolve_path(root: Path, raw_path: str) -> tuple[Path | None, str | None]:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, f"path points outside repository root: {raw_path}"
    return resolved, None


def _normalized_plan_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").casefold()
    return normalized[2:] if normalized.startswith("./") else normalized


def _fact_is_grounded(fact: re.Match[str], repo_root: Path) -> bool:
    resolved, error = _resolve_path(repo_root.resolve(), fact.group("path"))
    if error or resolved is None or not resolved.is_file():
        return False
    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    line_number = int(fact.group("line"))
    return (
        1 <= line_number <= len(lines)
        and fact.group("anchor").casefold() in lines[line_number - 1].casefold()
    )


def _validate_citations(document: MarkdownDocument, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    root = repo_root.resolve()
    for match in CITATION_RE.finditer(document.prose_text):
        raw_path = match.group("path")
        line_number = int(match.group("line"))
        resolved, error = _resolve_path(root, raw_path)
        source_line = _line_for(document.text, match.group(0))
        if error:
            diagnostics.append(Diagnostic("semantic.evidence.outside_repo", error, source_line))
            continue
        assert resolved is not None
        if not resolved.is_file():
            diagnostics.append(Diagnostic("semantic.evidence.missing_file", f"Cited file does not exist: {raw_path}", source_line))
            continue
        source_lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        if line_number < 1 or line_number > len(source_lines):
            diagnostics.append(Diagnostic(
                "semantic.evidence.line_out_of_range",
                f"Citation line {line_number} is outside {raw_path} (1-{len(source_lines)})",
                source_line,
            ))
    return diagnostics


def _validate_facts(document: MarkdownDocument, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    root = repo_root.resolve()
    for fact in FACT_RE.finditer(document.prose_text):
        raw_path = fact.group("path")
        line_number = int(fact.group("line"))
        anchor = fact.group("anchor")
        resolved, error = _resolve_path(root, raw_path)
        source_line = _line_for(document.text, fact.group(0))
        if error or resolved is None or not resolved.is_file():
            continue
        lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        if 1 <= line_number <= len(lines) and anchor.casefold() not in lines[line_number - 1].casefold():
            diagnostics.append(Diagnostic(
                "semantic.evidence.anchor_mismatch",
                f"{fact.group('id')} anchor {anchor!r} is absent from {raw_path}:{line_number}",
                source_line,
            ))
    return diagnostics


def _validate_changes(document: MarkdownDocument, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    root = repo_root.resolve()
    grounded_facts = [fact for fact in FACT_RE.finditer(document.prose_text) if _fact_is_grounded(fact, root)]
    for change in CHANGE_RE.finditer(document.prose_text):
        if change.group("status").casefold() == "new":
            continue
        raw_path = change.group("path")
        anchor = change.group("anchor")
        resolved, error = _resolve_path(root, raw_path)
        source_line = _line_for(document.text, change.group(0))
        if error:
            diagnostics.append(Diagnostic("semantic.change.outside_repo", error, source_line))
            continue
        assert resolved is not None
        if not resolved.is_file():
            diagnostics.append(Diagnostic("semantic.change.missing_file", f"Existing CH target does not exist: {raw_path}", source_line))
            continue
        source = resolved.read_text(encoding="utf-8", errors="replace")
        if anchor.casefold() not in source.casefold():
            diagnostics.append(Diagnostic(
                "semantic.change.missing_anchor",
                f"{change.group('id')} existing anchor {anchor!r} is absent from {raw_path}",
                source_line,
            ))
            continue
        change_path = _normalized_plan_path(raw_path)
        change_anchor = anchor.casefold()
        has_matching_fact = any(
            _normalized_plan_path(fact.group("path")) == change_path
            and (
                change_anchor in fact.group("anchor").casefold()
                or fact.group("anchor").casefold() in change_anchor
            )
            for fact in grounded_facts
        )
        if not has_matching_fact:
            diagnostics.append(Diagnostic(
                "semantic.change.ungrounded_anchor",
                f"{change.group('id')} existing anchor {anchor!r} needs a grounded F-n for the same path and anchor",
                source_line,
            ))
    return diagnostics


def _validate_ids_and_traceability(document: MarkdownDocument, tier: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    prose = document.prose_text
    defined_matches = [match.group("id") for match in ID_DEF_RE.finditer(prose)]
    for item_id, count in Counter(defined_matches).items():
        if count > 1:
            diagnostics.append(Diagnostic("semantic.ids.duplicate", f"{item_id} is defined {count} times", _line_for(document.text, item_id)))

    defined = set(defined_matches)
    for reference in {match.group("id") for match in ID_RE.finditer(prose)} - defined:
        diagnostics.append(Diagnostic("semantic.ids.orphan_reference", f"{reference} is referenced but not defined", _line_for(document.text, reference)))

    contract = load_contract()
    for kind in contract["tiers"][tier]["required_ids"]:
        if not definitions(document.text, kind):
            diagnostics.append(Diagnostic("semantic.ids.missing_required", f"{tier} plans must define at least one {kind}-n item"))

    trace = document.find_section("Traceability")
    trace_body = trace.body if trace else ""
    for criterion in sorted(definitions(document.text, "SC") | definitions(document.text, "C")):
        row = next(
            (
                line
                for line in trace_body.splitlines()
                if criterion in line and re.search(r"\bCH-\d+\b", line) and re.search(r"\bT-\d+\b", line)
            ),
            "",
        )
        if not re.search(r"\bCH-\d+\b", row) or not re.search(r"\bT-\d+\b", row):
            diagnostics.append(Diagnostic("semantic.traceability.criterion_unmapped", f"{criterion} must map to CH-n and T-n", _line_for(document.text, criterion)))
    for kind in ("CH", "T"):
        for item_id in sorted(definitions(document.text, kind)):
            if item_id not in trace_body:
                diagnostics.append(Diagnostic("semantic.traceability.unmapped_item", f"{item_id} must appear in Traceability", _line_for(document.text, item_id)))
    return diagnostics


def _validate_blueprints(document: MarkdownDocument, tier: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    implementation = document.find_section("Implementation Specification")
    malformed = [
        section
        for section in document.sections
        if section.level == 3
        and section.name.startswith("Execution Blueprint")
        and (implementation is None or implementation.line < section.line <= implementation.end_line)
        and BLUEPRINT_HEADING_RE.fullmatch(section.name) is None
    ]
    diagnostics.extend(
        Diagnostic(
            "semantic.blueprint.heading",
            "Execution blueprint heading must be 'Execution Blueprint: CH-n[, CH-n...] — purpose'",
            section.line,
        )
        for section in malformed
    )
    blueprints = execution_blueprints(document)
    if load_contract()["tiers"][tier]["blueprint_required"] and not blueprints:
        diagnostics.append(Diagnostic(
            "semantic.blueprint.missing",
            f"{tier} plans require at least one execution blueprint",
        ))
    defined_changes = definitions(document.text, "CH")
    for blueprint in blueprints:
        if not blueprint.has_artifact:
            diagnostics.append(Diagnostic(
                "semantic.blueprint.empty",
                "Execution blueprint requires a non-empty fenced block or Markdown table",
                blueprint.line,
            ))
        for change_id in blueprint.change_ids:
            if change_id not in defined_changes:
                diagnostics.append(Diagnostic(
                    "semantic.blueprint.orphan_change",
                    f"Execution blueprint references undefined {change_id}",
                    blueprint.line,
                ))
    return diagnostics


def _validate_risks(document: MarkdownDocument) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for line_number, line in enumerate(document.text.splitlines(), start=1):
        match = re.search(r"\b(R-\d+)\s+P([012])\s*:", line)
        if not match:
            continue
        if match.group(2) == "0" and re.search(r"\b(unresolved|open|unknown|TBD)\b", line, re.IGNORECASE):
            diagnostics.append(Diagnostic("semantic.risk.unresolved_p0", f"{match.group(1)} leaves a P0 unresolved", line_number))
        if match.group(2) in {"0", "1"}:
            if "Resolution:" not in line or not re.search(r"\bCH-\d+\b", line) or not re.search(r"\bT-\d+\b", line):
                diagnostics.append(Diagnostic("semantic.risk.resolution_missing", f"{match.group(1)} P0/P1 requires Resolution with CH-n and T-n", line_number))
    return diagnostics


def validate_semantics(text: str, tier: str, repo_root: Path | None = None) -> list[Diagnostic]:
    document = parse_markdown(text)
    diagnostics = list(document.diagnostics)
    diagnostics.extend(_validate_ids_and_traceability(document, tier))
    diagnostics.extend(_validate_blueprints(document, tier))
    diagnostics.extend(_validate_risks(document))
    root = (repo_root or Path.cwd()).resolve()
    diagnostics.extend(_validate_citations(document, root))
    diagnostics.extend(_validate_facts(document, root))
    diagnostics.extend(_validate_changes(document, root))
    return diagnostics


def coverage_summary(text: str, repo_root: Path | None = None) -> dict[str, int | bool]:
    document = parse_markdown(text)
    root = (repo_root or Path.cwd()).resolve()
    prose = document.prose_text
    facts = list(FACT_RE.finditer(prose))
    citations = list(CITATION_RE.finditer(prose))
    grounded_citations = 0
    for citation in citations:
        resolved, error = _resolve_path(root, citation.group("path"))
        if error or resolved is None or not resolved.is_file():
            continue
        line_count = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
        grounded_citations += 1 <= int(citation.group("line")) <= line_count
    values = {kind: len(definitions(text, kind)) for kind in ("SC", "F", "D", "CH", "T", "C", "R")}
    blueprints = execution_blueprints(document)
    blueprint_kinds = [kind for blueprint in blueprints for kind in blueprint.kinds]
    receipt_diagnostics = validate_receipt(text, required=True)
    return {
        "citations": len(citations),
        "grounded_citations": grounded_citations,
        "grounded_facts": sum(_fact_is_grounded(fact, root) for fact in facts),
        "success_criteria": values["SC"],
        "facts": values["F"],
        "decisions": values["D"],
        "changes": values["CH"],
        "tests": values["T"],
        "constraints": values["C"],
        "risks": values["R"],
        "code_blocks": len(document.code_blocks),
        "blueprints": len(blueprints),
        "pseudocode_blueprints": blueprint_kinds.count("pseudocode"),
        "mermaid_blueprints": blueprint_kinds.count("mermaid"),
        "code_blueprints": blueprint_kinds.count("code"),
        "table_blueprints": blueprint_kinds.count("table"),
        "blueprint_links_valid": not any(
            item.code == "semantic.blueprint.orphan_change"
            for item in _validate_blueprints(document, "tiny")
        ),
        "finalized": not any(item.code == "finalization.receipt.missing" for item in receipt_diagnostics),
        "receipt_valid": not receipt_diagnostics,
        "traceability_complete": not any(
            item.code.startswith("semantic.traceability")
            for item in _validate_ids_and_traceability(document, "standard")
        ),
    }
