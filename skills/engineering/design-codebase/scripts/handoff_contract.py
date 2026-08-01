"""Parse and validate the sole design-codebase handoff format."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from _diagnostic_contract import normalize_diagnostic

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
WORD_RE = re.compile(r"[a-z0-9]+")
TERM_STOPWORDS = {
    "and",
    "are",
    "because",
    "from",
    "into",
    "must",
    "that",
    "their",
    "these",
    "this",
    "those",
    "uses",
    "using",
    "while",
    "with",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f"line {self.line}: " if self.line is not None else ""
        return f"{self.code}: {location}{self.message}"

    def as_dict(
        self,
        *,
        path: str | Path = "design-handoff.md",
        next_command: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return normalize_diagnostic(
            asdict(self),
            skill="design-codebase",
            phase="validate",
            artifact="design-handoff",
            path=path,
            next_command=next_command,
        )


@dataclass(frozen=True)
class Evidence:
    identifier: str
    source: str
    locator: str
    claim: str
    anchor: str | None
    sha256: str | None
    line: int


@dataclass(frozen=True)
class StructuralDesign:
    boundary: str
    owner: str
    core_abstraction: str
    coupling_direction: str


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


def excerpt_sha256(lines: list[str], start: int, end: int) -> str:
    """Hash an inclusive excerpt using plan-contract v6 canonicalization."""
    excerpt = "\n".join(lines[start - 1 : end]) + "\n"
    return hashlib.sha256(excerpt.encode()).hexdigest()


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
            sha256=fields.get("sha256"),
            line=line,
        )
    if not evidence:
        diagnostics.append(Diagnostic("evidence.missing", "Evidence Ledger requires at least one evidence record."))
    return evidence, diagnostics


def _validate_local_evidence(
    item: Evidence,
    repo_root: Path,
    *,
    require_evidence_hashes: bool,
) -> list[Diagnostic]:
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
    if item.sha256 is None:
        if require_evidence_hashes:
            return [
                Diagnostic(
                    "evidence.sha256.missing",
                    f"[{item.identifier}] local evidence requires sha256 when evidence verification is enabled.",
                    item.line,
                )
            ]
        return []
    if not re.fullmatch(r"[0-9a-f]{64}", item.sha256):
        return [
            Diagnostic(
                "evidence.sha256.invalid",
                f"[{item.identifier}] sha256 must be exactly 64 lowercase hexadecimal characters.",
                item.line,
            )
        ]
    current_hash = excerpt_sha256(lines, start, end)
    if item.sha256 != current_hash:
        return [
            Diagnostic(
                "evidence.sha256.mismatch",
                f"[{item.identifier}] sha256 does not match current content at {item.locator}; evidence is stale.",
                item.line,
            )
        ]
    return []


def _validate_evidence(
    evidence: dict[str, Evidence],
    repo_root: Path,
    *,
    require_evidence_hashes: bool,
) -> list[Diagnostic]:
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
            diagnostics.extend(
                _validate_local_evidence(
                    item,
                    repo_root,
                    require_evidence_hashes=require_evidence_hashes,
                )
            )
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
        if item.source not in LOCAL_SOURCES and item.sha256 is not None:
            diagnostics.append(
                Diagnostic(
                    "evidence.sha256.unsupported",
                    f"[{item.identifier}] sha256 is supported only for code, test, configuration, and schema evidence.",
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
        "coupling_direction": _field_from_section(body, "Coupling direction"),
    }
    if not all(
        len(re.sub(r"[^a-z0-9]+", "", value.casefold())) >= 3
        and not PLACEHOLDER_RE.search(value)
        for value in values.values()
    ):
        return None
    return StructuralDesign(**values)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", CITATION_RE.sub("", value).casefold())


def _meaningful_terms(value: str) -> set[str]:
    without_citations = CITATION_RE.sub("", value)
    return {
        term
        for term in WORD_RE.findall(without_citations.casefold())
        if len(term) >= 4 and term not in TERM_STOPWORDS
    }


def _validate_depth_rationale(body: str) -> list[Diagnostic]:
    design = _field_from_section(body, "Design")
    hidden_details = _field_from_section(body, "Hidden details")
    exposed_controls = _field_from_section(body, "Exposed controls")
    rationale = _field_from_section(body, "Depth rationale")
    fields = (design, hidden_details, exposed_controls, rationale)
    rationale_terms = _meaningful_terms(rationale)
    hidden_terms = _meaningful_terms(hidden_details)
    exposed_terms = _meaningful_terms(exposed_controls)
    rationale_without_citations = CITATION_RE.sub("", rationale)
    restates_design = bool(design) and _normalized(rationale_without_citations) == _normalized(design)
    if (
        not all(_substantive(value) for value in fields)
        or not rationale_terms.intersection(hidden_terms)
        or not rationale_terms.intersection(exposed_terms)
        or restates_design
    ):
        return [
            Diagnostic(
                "design.depth.unsubstantiated",
                "Depth rationale must name a hidden detail and an exposed control without merely restating Design.",
            )
        ]
    return []


def _validate_alternatives(chosen_body: str, alternatives_body: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    chosen = _design(chosen_body)
    if chosen is None:
        diagnostics.append(
            Diagnostic(
                "chosen.structure.missing",
                "Chosen design requires substantive Boundary, Owner, Core abstraction, and Coupling direction fields.",
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
    alternatives: list[tuple[StructuralDesign, set[str]]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(alternatives_body)
        block = alternatives_body[start.end() : end]
        alternative = _design(block)
        if alternative is None:
            diagnostics.append(
                Diagnostic(
                    "alternative.structure.missing",
                    f"Alternative '{start.group('name').strip()}' requires substantive Boundary, Owner, Core abstraction, and Coupling direction fields.",
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
        alternatives.append((alternative, set(CITATION_RE.findall(block))))
    if alternatives and all(
        _normalized(item.core_abstraction) == _normalized(chosen.core_abstraction)
        for item, _citations in alternatives
    ):
        diagnostics.append(
            Diagnostic(
                "alternative.core.shared",
                "All alternatives share the chosen design's core abstraction.",
            )
        )
    structurally_distinct = [
        (item, citations)
        for item, citations in alternatives
        if _normalized(item.core_abstraction) != _normalized(chosen.core_abstraction)
        and (
            _normalized(item.boundary) != _normalized(chosen.boundary)
            or _normalized(item.owner) != _normalized(chosen.owner)
            or _normalized(item.coupling_direction) != _normalized(chosen.coupling_direction)
        )
    ]
    if alternatives and not structurally_distinct:
        diagnostics.append(
            Diagnostic(
                "alternative.structural.none",
                "At least one alternative must change the core abstraction and the boundary, owner, or coupling direction.",
            )
        )
    chosen_citations = set(CITATION_RE.findall(chosen_body))
    if structurally_distinct and not any(
        citations - chosen_citations for _item, citations in structurally_distinct
    ):
        diagnostics.append(
            Diagnostic(
                "alternative.no_distinct_evidence",
                "At least one structurally distinct alternative must cite evidence not cited by the chosen design rationale.",
            )
        )
    return diagnostics


def _claim_support_diagnostics(
    value: str,
    label: str,
    evidence: dict[str, Evidence],
) -> list[Diagnostic]:
    if not value:
        return []
    citations = set(CITATION_RE.findall(value))
    if not citations:
        return [
            Diagnostic(
                "design.claim.uncited",
                f"Design claim '{label}' requires an inline evidence citation.",
            )
        ]
    if not any(
        identifier in evidence and evidence[identifier].source in LOCAL_SOURCES
        for identifier in citations
    ):
        return [
            Diagnostic(
                "design.claim.repository_evidence_missing",
                f"Design claim '{label}' requires code, test, configuration, or schema evidence.",
            )
        ]
    return []


def _validate_design_claim_support(
    chosen_body: str,
    alternatives_body: str,
    sections: dict[str, str],
    evidence: dict[str, Evidence],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for field in (
        "Boundary",
        "Owner",
        "Core abstraction",
        "Coupling direction",
        "Design",
        "Hidden details",
        "Exposed controls",
        "Depth rationale",
    ):
        diagnostics.extend(
            _claim_support_diagnostics(
                _field_from_section(chosen_body, field),
                f"chosen {field}",
                evidence,
            )
        )

    starts = list(re.finditer(r"^### Alternative:\s*(?P<name>.+)$", alternatives_body, re.MULTILINE))
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(alternatives_body)
        block = alternatives_body[start.end() : end]
        name = start.group("name").strip()
        for field in ("Boundary", "Owner", "Core abstraction", "Coupling direction", "Rejected because"):
            diagnostics.extend(
                _claim_support_diagnostics(
                    _field_from_section(block, field),
                    f"alternative '{name}' {field}",
                    evidence,
                )
            )

    optional_fields = ("Volatility", "Propagation", "Locality", "Deletion test", "Second-use test")
    for section_name, body in sections.items():
        if section_name == EVIDENCE_HEADING:
            continue
        for field in optional_fields:
            for match in re.finditer(
                rf"^- {re.escape(field)}:\s*(?P<value>.+)$",
                body,
                re.MULTILINE | re.IGNORECASE,
            ):
                diagnostics.extend(
                    _claim_support_diagnostics(
                        match.group("value").strip(),
                        f"{section_name} {field}",
                        evidence,
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


def _validate_consolidation(body: str) -> list[Diagnostic]:
    statements = re.split(r"(?<=[.!?])\s+", body)
    not_applicable = [statement for statement in statements if "not applicable" in statement.casefold()]
    if not_applicable:
        if any(CITATION_RE.search(statement) for statement in not_applicable):
            return []
    else:
        option = re.search(r"\b(?:consolidat\w*|combin\w*|merg\w*|co-?locat\w*)\b", body, re.IGNORECASE)
        reason = re.search(r"\b(?:because|due to|rejected|therefore|but|while|so that)\b", body, re.IGNORECASE)
        structural_reason = re.search(
            r"\b(?:owners?|ownership|coupl\w*|boundar\w*)\b",
            body,
            re.IGNORECASE,
        )
        if option and reason and structural_reason:
            return []
    return [
        Diagnostic(
            "consolidation.reasoning.missing",
            "Consolidation Considered requires a cited not-applicable statement or an option with ownership, coupling, or boundary reasoning.",
        )
    ]


def _interface_table_terms(body: str) -> set[str]:
    rows = [
        line
        for line in body.splitlines()
        if line.strip().startswith("|")
        and not re.fullmatch(r"\s*\|(?:\s*:?-+:?\s*\|)+\s*", line)
    ]
    return _meaningful_terms("\n".join(rows))


def _validate_documentation(interface_body: str, documentation_body: str) -> list[Diagnostic]:
    documentation_terms = _meaningful_terms(documentation_body)
    if documentation_terms and documentation_terms <= _interface_table_terms(interface_body):
        return [
            Diagnostic(
                "documentation.signature_restatement",
                "Documentation Obligations must describe caller knowledge beyond the Target Interface Contract table.",
            )
        ]
    return []


def _design_term_coverage(question_body: str, design: StructuralDesign) -> float:
    question_terms = _meaningful_terms(question_body)
    coverages: list[float] = []
    for value in (design.boundary, design.owner, design.core_abstraction):
        terms = _meaningful_terms(value)
        if terms:
            coverages.append(len(question_terms.intersection(terms)) / len(terms))
    return max(coverages, default=0.0)


def _validate_planner_questions(chosen_body: str, questions_body: str) -> list[Diagnostic]:
    statements = re.split(r"(?<=[.!?])\s+", questions_body)
    explicit_none = [
        statement
        for statement in statements
        if re.search(r"\b(?:none|no open questions?)\b", statement, re.IGNORECASE)
    ]
    if explicit_none and any(CITATION_RE.search(statement) for statement in explicit_none):
        return []

    scoped_to_planning = re.search(r"\b(?:ground\w*|reconcil\w*)\b", questions_body, re.IGNORECASE)
    decision_language = re.search(
        r"\b(?:should|whether|reconsider|re-decide|decide|choose|change)\b",
        questions_body,
        re.IGNORECASE,
    )
    chosen = _design(chosen_body)
    redecides_design = bool(
        decision_language
        and chosen
        and (
            re.search(r"\b(?:boundary|owner|ownership|core abstraction)\b", questions_body, re.IGNORECASE)
            or _design_term_coverage(questions_body, chosen) >= 0.6
        )
    )
    if not scoped_to_planning or redecides_design:
        return [
            Diagnostic(
                "planner_questions.redecides_design",
                "Planner questions must be limited to grounding or reconciliation and must not reopen the chosen design.",
            )
        ]
    return []


def validate_handoff(
    text: str,
    repo_root: Path,
    *,
    require_evidence_hashes: bool = False,
) -> tuple[ParsedHandoff, list[Diagnostic]]:
    """Parse and validate one design handoff against the current repository."""
    normalized = normalize_markdown(text)
    resolved_root = repo_root.resolve()
    sections, diagnostics = _parse_sections(normalized)
    diagnostics.extend(_validate_title(normalized))
    evidence, evidence_diagnostics = _parse_evidence(sections.get(EVIDENCE_HEADING, ""), normalized)
    diagnostics.extend(evidence_diagnostics)
    diagnostics.extend(
        _validate_evidence(
            evidence,
            resolved_root,
            require_evidence_hashes=require_evidence_hashes,
        )
    )

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
    chosen_body = sections.get("Chosen Design & Depth Rationale", "")
    interface_body = sections.get("Target Interface Contract", "")
    diagnostics.extend(
        _validate_design_claim_support(
            chosen_body,
            sections.get("Alternatives Considered", ""),
            sections,
            evidence,
        )
    )
    diagnostics.extend(_validate_depth_rationale(chosen_body))
    diagnostics.extend(_validate_interface(interface_body))
    diagnostics.extend(_validate_generality(sections.get("Generality Justification", "")))
    diagnostics.extend(_validate_consolidation(sections.get("Consolidation Considered", "")))
    diagnostics.extend(
        _validate_documentation(
            interface_body,
            sections.get("Documentation Obligations", ""),
        )
    )
    diagnostics.extend(
        _validate_planner_questions(
            chosen_body,
            sections.get("Open Questions for the Planner", ""),
        )
    )
    return ParsedHandoff(sections=sections, evidence=evidence), diagnostics


def backfill_evidence_hashes(text: str, repo_root: Path) -> str:
    """Insert missing hashes for valid local evidence records."""
    normalized = normalize_markdown(text)
    sections, section_diagnostics = _parse_sections(normalized)
    if section_diagnostics:
        raise ValueError("cannot backfill evidence hashes in an invalid handoff shape")
    ledger_body = sections.get(EVIDENCE_HEADING, "")
    evidence, evidence_diagnostics = _parse_evidence(ledger_body, normalized)
    if evidence_diagnostics:
        raise ValueError("cannot backfill malformed evidence records")

    replacements: dict[str, str] = {}
    resolved_root = repo_root.resolve()
    for item in evidence.values():
        if item.source not in LOCAL_SOURCES or item.sha256 is not None:
            continue
        locator = LOCAL_LOCATOR_RE.fullmatch(item.locator)
        if locator is None:
            raise ValueError(f"[{item.identifier}] has an invalid local locator")
        target = (resolved_root / Path(locator.group("path"))).resolve()
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = int(locator.group("start"))
        end = int(locator.group("end") or start)
        replacements[item.identifier] = excerpt_sha256(lines, start, end)

    def insert_hash(match: re.Match[str]) -> str:
        identifier = match.group("id")
        digest = replacements.get(identifier)
        if digest is None:
            return match.group(0)
        fields = match.group("fields")
        marker = " | claim:"
        claim_offset = fields.find(marker)
        if claim_offset < 0:
            raise ValueError(f"[{identifier}] has no claim field")
        with_hash = fields[:claim_offset] + f" | sha256: {digest}" + fields[claim_offset:]
        return f"- [{identifier}] {with_hash}"

    hashed_ledger = EVIDENCE_RE.sub(insert_hash, ledger_body)
    ledger_offset = normalized.find(ledger_body)
    if ledger_offset < 0:
        raise ValueError("cannot locate Evidence Ledger content")
    return normalized[:ledger_offset] + hashed_ledger + normalized[ledger_offset + len(ledger_body) :]
