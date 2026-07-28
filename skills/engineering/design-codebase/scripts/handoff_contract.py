"""Parse and validate the sole design-codebase handoff format."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

EVIDENCE_HEADING = "Evidence Ledger"
REQUIRED_SECTIONS = (
    "Problem & Scope",
    "Chosen Design & Depth Rationale",
    "Alternatives Considered",
    "Target Interface Contract",
    "Generality Justification",
    "Consolidation Considered",
    "Documentation Obligations",
    "Open Questions for the Planner",
)
EXPECTED_HEADINGS = (EVIDENCE_HEADING, *REQUIRED_SECTIONS)
LOCAL_SOURCES = {"code", "test", "configuration", "schema"}
EVIDENCE_SOURCES = {"request", *LOCAL_SOURCES, "runtime", "external"}

HEADING_RE = re.compile(r"^## (?P<name>.+?)\s*$", re.MULTILINE)
TITLE_RE = re.compile(r"^# Design Handoff:\s*(?P<title>.+?)\s*$", re.MULTILINE)
EVIDENCE_RE = re.compile(r"^- \[(?P<id>E-[1-9]\d*)\]\s+(?P<fields>.+)$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(E-[1-9]\d*)\]")
LOCAL_LOCATOR_RE = re.compile(
    r"^(?P<path>.+):(?P<start>[1-9]\d*)(?:-(?P<end>[1-9]\d*))?$"
)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TODO|FIXME|REPLACE(?:_[A-Z0-9_]+)?|INSERT HERE|AS NEEDED)\b|\{\{[^}\n]+\}\}",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f"line {self.line}: " if self.line is not None else ""
        return f"{self.code}: {location}{self.message}"

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    identifier: str
    source: str
    locator: str
    claim: str
    anchor: str | None
    line: int


@dataclass(frozen=True)
class StructuralDesign:
    boundary: str
    owner: str
    core_abstraction: str


@dataclass(frozen=True)
class ParsedHandoff:
    sections: dict[str, str]
    evidence: dict[str, Evidence]


def normalize_markdown(text: str) -> str:
    """Normalize line endings and trailing whitespace with one final newline."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.strip().splitlines()) + "\n"


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _fields(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in raw.split(" | "):
        key, separator, value = part.partition(":")
        if separator:
            values[key.strip().casefold()] = value.strip()
    return values


def _field_from_section(body: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}:\s*(?P<value>.+)$", body, re.MULTILINE | re.IGNORECASE)
    return match.group("value").strip() if match else ""


def _substantive(value: str) -> bool:
    without_citations = CITATION_RE.sub("", value)
    plain = re.sub(r"[#*_`|[\]():-]", " ", without_citations)
    return len(re.sub(r"\s+", " ", plain).strip()) >= 16 and not PLACEHOLDER_RE.search(value)


def _parse_sections(text: str) -> tuple[dict[str, str], list[Diagnostic]]:
    matches = list(HEADING_RE.finditer(text))
    names = [match.group("name").strip() for match in matches]
    diagnostics: list[Diagnostic] = []
    for expected in EXPECTED_HEADINGS:
        count = names.count(expected)
        if count == 0:
            diagnostics.append(Diagnostic("section.missing", f"Missing required section '## {expected}'."))
        elif count > 1:
            diagnostics.append(Diagnostic("section.duplicate", f"Section '## {expected}' appears {count} times."))
    for index, name in enumerate(names):
        if name not in EXPECTED_HEADINGS:
            diagnostics.append(
                Diagnostic(
                    "section.unknown",
                    f"Unknown level-two section '## {name}'.",
                    _line_number(text, matches[index].start()),
                )
            )
    if names != list(EXPECTED_HEADINGS):
        diagnostics.append(
            Diagnostic(
                "section.order",
                "Level-two headings must be exactly: " + ", ".join(EXPECTED_HEADINGS) + ".",
            )
        )
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group("name").strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(name, text[match.end() : end].strip())
    return sections, diagnostics


def _validate_title(text: str) -> list[Diagnostic]:
    matches = list(TITLE_RE.finditer(text))
    if len(matches) != 1:
        return [
            Diagnostic(
                "title.invalid",
                "Handoff requires exactly one '# Design Handoff: TITLE' heading.",
            )
        ]
    if not _substantive(matches[0].group("title")):
        return [Diagnostic("title.placeholder", "Design handoff title must be substantive.")]
    return []


def _parse_evidence(body: str, full_text: str) -> tuple[dict[str, Evidence], list[Diagnostic]]:
    evidence: dict[str, Evidence] = {}
    diagnostics: list[Diagnostic] = []
    ledger_offset = full_text.find(body)
    for match in EVIDENCE_RE.finditer(body):
        identifier = match.group("id")
        line = _line_number(full_text, max(0, ledger_offset) + match.start())
        if identifier in evidence:
            diagnostics.append(
                Diagnostic("evidence.duplicate", f"Evidence identifier [{identifier}] is duplicated.", line)
            )
            continue
        fields = _fields(match.group("fields"))
        missing = [name for name in ("source", "locator", "claim") if not fields.get(name)]
        if missing:
            diagnostics.append(
                Diagnostic(
                    "evidence.fields.missing",
                    f"[{identifier}] is missing: {', '.join(missing)}.",
                    line,
                )
            )
            continue
        evidence[identifier] = Evidence(
            identifier=identifier,
            source=fields["source"].casefold(),
            locator=fields["locator"],
            claim=fields["claim"],
            anchor=fields.get("anchor"),
            line=line,
        )
    if not evidence:
        diagnostics.append(Diagnostic("evidence.missing", "Evidence Ledger requires at least one evidence record."))
    return evidence, diagnostics


def _validate_local_evidence(item: Evidence, repo_root: Path) -> list[Diagnostic]:
    match = LOCAL_LOCATOR_RE.fullmatch(item.locator)
    if not match:
        return [
            Diagnostic(
                "evidence.locator.invalid",
                f"[{item.identifier}] local evidence requires relative path:start-end.",
                item.line,
            )
        ]
    relative = Path(match.group("path"))
    if relative.is_absolute():
        return [
            Diagnostic(
                "evidence.path.absolute",
                f"[{item.identifier}] repository locator must be relative.",
                item.line,
            )
        ]
    target = (repo_root / relative).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError:
        return [
            Diagnostic(
                "evidence.path.escape",
                f"[{item.identifier}] locator escapes the repository.",
                item.line,
            )
        ]
    if not target.is_file():
        return [
            Diagnostic(
                "evidence.path.missing",
                f"[{item.identifier}] cited file does not exist: {relative.as_posix()}.",
                item.line,
            )
        ]
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start or end > len(lines):
        return [
            Diagnostic(
                "evidence.lines.invalid",
                f"[{item.identifier}] line range {start}-{end} is outside the {len(lines)}-line file.",
                item.line,
            )
        ]
    if item.anchor and item.anchor not in "\n".join(lines[start - 1 : end]):
        return [
            Diagnostic(
                "evidence.anchor.missing",
                f"[{item.identifier}] anchor '{item.anchor}' is absent from the cited range.",
                item.line,
            )
        ]
    return []


def _validate_evidence(evidence: dict[str, Evidence], repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for item in evidence.values():
        if item.source not in EVIDENCE_SOURCES:
            diagnostics.append(
                Diagnostic(
                    "evidence.source.invalid",
                    f"[{item.identifier}] source must be one of {sorted(EVIDENCE_SOURCES)}.",
                    item.line,
                )
            )
        elif item.source in LOCAL_SOURCES:
            diagnostics.extend(_validate_local_evidence(item, repo_root))
        elif item.source == "request" and item.locator != "user-request":
            diagnostics.append(
                Diagnostic(
                    "evidence.request.locator",
                    f"[{item.identifier}] request evidence locator must be 'user-request'.",
                    item.line,
                )
            )
        elif item.source == "external" and not re.match(r"^https?://\S+$", item.locator):
            diagnostics.append(
                Diagnostic(
                    "evidence.external.locator",
                    f"[{item.identifier}] external evidence requires an HTTP(S) URL.",
                    item.line,
                )
            )
        if not _substantive(item.claim):
            diagnostics.append(
                Diagnostic(
                    "evidence.claim.placeholder",
                    f"[{item.identifier}] claim must be substantive and contain no placeholder.",
                    item.line,
                )
            )
    return diagnostics


def _design(body: str) -> StructuralDesign | None:
    values = {
        "boundary": _field_from_section(body, "Boundary"),
        "owner": _field_from_section(body, "Owner"),
        "core_abstraction": _field_from_section(body, "Core abstraction"),
    }
    if not all(
        len(re.sub(r"[^a-z0-9]+", "", value.casefold())) >= 3
        and not PLACEHOLDER_RE.search(value)
        for value in values.values()
    ):
        return None
    return StructuralDesign(**values)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _validate_alternatives(chosen_body: str, alternatives_body: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    chosen = _design(chosen_body)
    if chosen is None:
        diagnostics.append(
            Diagnostic(
                "chosen.structure.missing",
                "Chosen design requires substantive Boundary, Owner, and Core abstraction fields.",
            )
        )
        return diagnostics
    starts = list(re.finditer(r"^### Alternative:\s*(?P<name>.+)$", alternatives_body, re.MULTILINE))
    if not starts:
        return [
            Diagnostic(
                "alternative.missing",
                "Alternatives Considered requires at least one '### Alternative: NAME' block.",
            )
        ]
    alternatives: list[StructuralDesign] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(alternatives_body)
        block = alternatives_body[start.end() : end]
        alternative = _design(block)
        if alternative is None:
            diagnostics.append(
                Diagnostic(
                    "alternative.structure.missing",
                    f"Alternative '{start.group('name').strip()}' requires substantive Boundary, Owner, and Core abstraction fields.",
                )
            )
            continue
        rejection = _field_from_section(block, "Rejected because")
        if not _substantive(rejection) or not CITATION_RE.search(rejection):
            diagnostics.append(
                Diagnostic(
                    "alternative.rejection.invalid",
                    f"Alternative '{start.group('name').strip()}' needs a substantive, cited rejection.",
                )
            )
        alternatives.append(alternative)
    if alternatives and all(
        _normalized(item.core_abstraction) == _normalized(chosen.core_abstraction) for item in alternatives
    ):
        diagnostics.append(
            Diagnostic(
                "alternative.core.shared",
                "All alternatives share the chosen design's core abstraction.",
            )
        )
    distinct = any(
        _normalized(item.core_abstraction) != _normalized(chosen.core_abstraction)
        and (
            _normalized(item.boundary) != _normalized(chosen.boundary)
            or _normalized(item.owner) != _normalized(chosen.owner)
        )
        for item in alternatives
    )
    if alternatives and not distinct:
        diagnostics.append(
            Diagnostic(
                "alternative.structural.none",
                "At least one alternative must change the core abstraction and the boundary or owner.",
            )
        )
    return diagnostics


def _validate_interface(body: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for term in ("Today", "Proposed", "Signature", "Defaults", "Nullability", "Caller-visible errors"):
        if not re.search(rf"\b{re.escape(term)}\b", body, re.IGNORECASE):
            diagnostics.append(
                Diagnostic("interface.comparison.missing", f"Target Interface Contract must compare '{term}'.")
            )
    match = re.search(
        r"^- Error surface direction:\s*(?P<direction>[A-Za-z-]+)\s*$",
        body,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match or match.group("direction").casefold() not in {"shrink", "flat", "grow"}:
        diagnostics.append(
            Diagnostic(
                "interface.error_direction.invalid",
                "Error surface direction must be exactly shrink, flat, or grow.",
            )
        )
        return diagnostics
    rationale = _field_from_section(body, "Error surface justification")
    if not _substantive(rationale):
        diagnostics.append(
            Diagnostic(
                "interface.error_justification.missing",
                "Error surface justification must be substantive.",
            )
        )
    if match.group("direction").casefold() == "grow" and not CITATION_RE.search(rationale):
        diagnostics.append(
            Diagnostic(
                "interface.error_growth.uncited",
                "A growing error surface requires a cited justification.",
            )
        )
    return diagnostics


def _validate_generality(body: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    citations = set(CITATION_RE.findall(body))
    intentionally_narrow = "intentionally narrow" in body.casefold()
    if not intentionally_narrow and len(citations) < 2:
        diagnostics.append(
            Diagnostic(
                "generality.patterns.insufficient",
                "A general design requires citations for at least two distinct present-day use patterns.",
            )
        )
    if "third" not in body.casefold():
        diagnostics.append(
            Diagnostic(
                "generality.third_pattern.missing",
                "Generality Justification must state what a third use pattern would change.",
            )
        )
    return diagnostics


def validate_handoff(text: str, repo_root: Path) -> tuple[ParsedHandoff, list[Diagnostic]]:
    """Parse and validate one design handoff against the current repository."""
    normalized = normalize_markdown(text)
    resolved_root = repo_root.resolve()
    sections, diagnostics = _parse_sections(normalized)
    diagnostics.extend(_validate_title(normalized))
    evidence, evidence_diagnostics = _parse_evidence(sections.get(EVIDENCE_HEADING, ""), normalized)
    diagnostics.extend(evidence_diagnostics)
    diagnostics.extend(_validate_evidence(evidence, resolved_root))

    for name in REQUIRED_SECTIONS:
        body = sections.get(name, "")
        if not _substantive(body):
            diagnostics.append(
                Diagnostic(
                    "section.content.invalid",
                    f"Section '## {name}' must be substantive and contain no placeholder.",
                )
            )
        citations = set(CITATION_RE.findall(body))
        if not citations:
            diagnostics.append(
                Diagnostic("section.citation.missing", f"Section '## {name}' requires evidence citation.")
            )
        for identifier in sorted(citations - set(evidence)):
            diagnostics.append(
                Diagnostic(
                    "section.citation.undefined",
                    f"Section '## {name}' cites undefined evidence [{identifier}].",
                )
            )

    diagnostics.extend(
        _validate_alternatives(
            sections.get("Chosen Design & Depth Rationale", ""),
            sections.get("Alternatives Considered", ""),
        )
    )
    diagnostics.extend(_validate_interface(sections.get("Target Interface Contract", "")))
    diagnostics.extend(_validate_generality(sections.get("Generality Justification", "")))
    return ParsedHandoff(sections=sections, evidence=evidence), diagnostics
