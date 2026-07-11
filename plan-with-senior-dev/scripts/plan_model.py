"""Structured Markdown model and semantic checks for implementation plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from _plan_utils import Diagnostic


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})([A-Za-z0-9_-]*)\s*$")
CITATION_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:[\\/])?(?:[A-Za-z0-9_@+ .()~-]+[\\/])*"
    r"[A-Za-z0-9_@+~()-]+\.[A-Za-z0-9_-]+):(?P<line>\d+)"
)
ID_RE = re.compile(r"\b(?P<kind>SC|CH|T|C|R)-(?P<number>[1-9]\d*)\b")
ID_DEF_RE = re.compile(r"\b(?P<id>(?:SC|CH|T|C|R)-[1-9]\d*)\s*:")


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
        for raw_line in self.body.splitlines():
            line = raw_line.strip()
            if line and not FENCE_RE.match(raw_line):
                return True
        return False


@dataclass(frozen=True)
class MarkdownDocument:
    text: str
    sections: tuple[Section, ...]
    code_blocks: tuple[CodeBlock, ...]
    diagnostics: tuple[Diagnostic, ...]

    def find_section(self, *names: str) -> Section | None:
        normalized = {name.casefold() for name in names}
        for item in self.sections:
            if item.name.casefold() in normalized:
                return item
        return None


def parse_markdown(text: str) -> MarkdownDocument:
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []
    blocks: list[CodeBlock] = []
    diagnostics: list[Diagnostic] = []
    fence_marker: str | None = None
    fence_language = ""
    fence_start = 0
    fence_body_start = 0

    for index, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
                fence_language = fence.group(2).casefold()
                fence_start = index
                fence_body_start = index
            elif marker[0] == fence_marker:
                body = "\n".join(lines[fence_body_start:index - 1])
                blocks.append(CodeBlock(fence_language, body, fence_start, index))
                fence_marker = None
            continue

        if fence_marker is None:
            heading = HEADING_RE.match(line)
            if heading:
                headings.append((index, len(heading.group(1)), heading.group(2).strip()))

    if fence_marker is not None:
        body = "\n".join(lines[fence_body_start:])
        blocks.append(CodeBlock(fence_language, body, fence_start, None))
        diagnostics.append(Diagnostic(
            code="markdown.fence.unclosed",
            message="Fenced code block is not closed",
            line=fence_start,
        ))

    sections: list[Section] = []
    for position, (line_number, level, name) in enumerate(headings):
        next_line = len(lines) + 1
        for candidate_line, candidate_level, _ in headings[position + 1:]:
            if candidate_level <= level:
                next_line = candidate_line
                break
        body = "\n".join(lines[line_number:next_line - 1])
        sections.append(Section(name=name, level=level, line=line_number, body=body))

    return MarkdownDocument(text, tuple(sections), tuple(blocks), tuple(diagnostics))


def _section_body(document: MarkdownDocument, *names: str) -> str:
    found = document.find_section(*names)
    return found.body if found else ""


def _definitions(text: str, kind: str) -> set[str]:
    return {
        match.group("id")
        for match in ID_DEF_RE.finditer(text)
        if match.group("id").startswith(f"{kind}-")
    }


def _line_for(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def _trace_row(body: str, item_id: str) -> str | None:
    for line in body.splitlines():
        if item_id in line and re.search(r"\bCH-\d+\b", line) and re.search(r"\bT-\d+\b", line):
            return line
    return None


def _validate_citations(document: MarkdownDocument, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    root = repo_root.resolve()
    seen: set[tuple[str, int]] = set()
    for match in CITATION_RE.finditer(document.text):
        raw_path = match.group("path").strip(" `[]()")
        line_number = int(match.group("line"))
        if raw_path.startswith(("http://", "https://")):
            continue
        key = (raw_path, line_number)
        if key in seen:
            continue
        seen.add(key)
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            diagnostics.append(Diagnostic(
                code="semantic.evidence.outside_repo",
                message=f"Citation points outside repository root: {raw_path}:{line_number}",
                line=_line_for(document.text, match.group(0)),
            ))
            continue
        if not resolved.is_file():
            diagnostics.append(Diagnostic(
                code="semantic.evidence.missing_file",
                message=f"Cited file does not exist: {raw_path}",
                line=_line_for(document.text, match.group(0)),
            ))
            continue
        try:
            count = sum(1 for _ in resolved.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            diagnostics.append(Diagnostic(
                code="semantic.evidence.unreadable",
                message=f"Cannot read cited file {raw_path}: {exc}",
            ))
            continue
        if line_number < 1 or line_number > max(count, 1):
            diagnostics.append(Diagnostic(
                code="semantic.evidence.line_out_of_range",
                message=f"Citation line {line_number} is outside {raw_path} (1-{count})",
                line=_line_for(document.text, match.group(0)),
            ))
    return diagnostics


def _validate_traceability(document: MarkdownDocument, tier: str) -> list[Diagnostic]:
    if tier == "tiny":
        return []

    diagnostics: list[Diagnostic] = []
    trace_body = _section_body(
        document,
        "Traceability and Constraints",
        "Change Propagation Map",
        "Change Propagation",
        "Propagation Map",
        "Constraint Verification",
    )
    verification_body = _section_body(document, "Verification and Risks", "Test Strategy", "Test/Verification")
    implementation_body = _section_body(
        document,
        "Implementation Specification",
        "Changes",
        "Logic Specification",
    )

    success_ids = _definitions(document.text, "SC")
    change_ids = _definitions(document.text, "CH")
    test_ids = _definitions(document.text, "T")
    constraint_ids = _definitions(document.text, "C")

    for kind, values in (("SC", success_ids), ("CH", change_ids), ("T", test_ids)):
        if not values:
            diagnostics.append(Diagnostic(
                code=f"semantic.traceability.missing_{kind.casefold()}_ids",
                message=f"{tier} plans must define stable {kind}-n traceability IDs",
            ))

    for success_id in sorted(success_ids):
        row = _trace_row(trace_body, success_id)
        if row is None:
            diagnostics.append(Diagnostic(
                code="semantic.traceability.criterion_unmapped",
                message=f"{success_id} must map to CH-n and T-n in traceability",
                line=_line_for(document.text, success_id),
            ))
            continue
        test_match = re.search(r"\bT-\d+\b", row)
        change_match = re.search(r"\bCH-\d+\b", row)
        if change_match and change_match.group(0) not in implementation_body:
            diagnostics.append(Diagnostic(
                code="semantic.traceability.change_missing_implementation",
                message=f"{change_match.group(0)} is mapped from {success_id} but not defined in implementation",
            ))
        if test_match and test_match.group(0) not in verification_body:
            diagnostics.append(Diagnostic(
                code="semantic.traceability.test_missing_verification",
                message=f"{test_match.group(0)} is mapped from {success_id} but not defined in verification",
            ))

    for constraint_id in sorted(constraint_ids):
        row = _trace_row(trace_body, constraint_id)
        if row is None:
            diagnostics.append(Diagnostic(
                code="semantic.constraints.unmapped",
                message=f"{constraint_id} must map to CH-n and T-n",
                line=_line_for(document.text, constraint_id),
            ))
        definition_line = next((line for line in document.text.splitlines() if f"{constraint_id}:" in line), "")
        if re.search(r"\b(modified|at[- ]risk)\b", definition_line, flags=re.IGNORECASE):
            if not re.search(r"\b(rollback|revert|restore|disable|forward recovery)\b", trace_body + verification_body, flags=re.IGNORECASE):
                diagnostics.append(Diagnostic(
                    code="semantic.constraints.rollback_missing",
                    message=f"{constraint_id} is modified or at risk but lacks rollback or recovery",
                ))

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        if re.search(r"update required\s*:\s*yes", line, flags=re.IGNORECASE) and not re.search(r"\bCH-\d+\b", line):
            diagnostics.append(Diagnostic(
                code="semantic.propagation.owner_missing",
                message="Propagation entry requiring an update must name its CH-n owner",
                line=line_number,
            ))

    return diagnostics


def _validate_risks(document: MarkdownDocument) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for line_number, line in enumerate(document.text.splitlines(), start=1):
        if not re.search(r"\bR-\d+\b", line) or not re.search(r"\bP[01]\b", line):
            continue
        missing = []
        if not re.search(r"\b(Action|Resolution)\s*:", line, flags=re.IGNORECASE):
            missing.append("Action/Resolution")
        if not re.search(r"\b(?:Owner\s*:\s*)?(?:CH|T)-\d+\b", line, flags=re.IGNORECASE):
            missing.append("CH-n/T-n owner")
        if missing:
            diagnostics.append(Diagnostic(
                code="semantic.risk.action_owner_missing",
                message=f"P0/P1 risk is missing {', '.join(missing)}",
                line=line_number,
            ))
    return diagnostics


def _validate_contradictions(document: MarkdownDocument) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for line_number, line in enumerate(document.text.splitlines(), start=1):
        lowered = line.casefold()
        if "assert" not in lowered and "return" not in lowered and "output" not in lowered:
            continue
        true_claim = bool(re.search(r"\b(?:assert|return|returns|output)\b[^.\n]{0,50}\btrue\b", lowered))
        false_claim = bool(re.search(r"\b(?:assert|return|returns|output)\b[^.\n]{0,50}\bfalse\b", lowered))
        if true_claim and false_claim:
            diagnostics.append(Diagnostic(
                code="semantic.expectation.contradiction",
                message="The same scenario requires incompatible true and false results",
                line=line_number,
            ))
    return diagnostics


def _validate_interface_evidence(document: MarkdownDocument) -> list[Diagnostic]:
    implementation = _section_body(document, "Implementation Specification", "Changes", "Approach")
    evidence = _section_body(document, "Evidence and Decisions", "Current State", "Evidence")
    if not re.search(r"\b(API|schema|interface|event|command|public contract)\b", implementation, flags=re.IGNORECASE):
        return []
    if not document.code_blocks:
        return [Diagnostic(
            code="semantic.interface.shape_missing",
            message="Interface changes must include the complete proposed shape in a code block",
        )]
    if not CITATION_RE.search(evidence):
        return [Diagnostic(
            code="semantic.interface.current_evidence_missing",
            message="Interface changes must cite the current signature or schema in evidence",
        )]
    return []


def validate_semantics(text: str, tier: str, repo_root: Path | None = None) -> list[Diagnostic]:
    document = parse_markdown(text)
    diagnostics = list(document.diagnostics)
    diagnostics.extend(_validate_traceability(document, tier))
    diagnostics.extend(_validate_risks(document))
    diagnostics.extend(_validate_contradictions(document))
    diagnostics.extend(_validate_interface_evidence(document))
    if repo_root is not None:
        diagnostics.extend(_validate_citations(document, repo_root))
    return diagnostics


def coverage_summary(text: str) -> dict[str, int | bool]:
    document = parse_markdown(text)
    ids = {kind: len(_definitions(text, kind)) for kind in ("SC", "CH", "T", "C", "R")}
    return {
        "citations": len({match.group(0) for match in CITATION_RE.finditer(text)}),
        "success_criteria": ids["SC"],
        "changes": ids["CH"],
        "tests": ids["T"],
        "constraints": ids["C"],
        "risks": ids["R"],
        "code_blocks": len(document.code_blocks),
        "traceability_complete": not any(
            diagnostic.code.startswith("semantic.traceability")
            for diagnostic in _validate_traceability(document, "standard")
        ),
    }
