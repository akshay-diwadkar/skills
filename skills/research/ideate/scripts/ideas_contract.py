#!/usr/bin/env python3
"""Parse and validate the sole ideas.md handoff format.

Deterministic, standard-library-only. No model calls, web requests, or
external dependencies.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _diagnostic_contract import normalize_diagnostic

# ---------------------------------------------------------------------------
# Structural constants
# ---------------------------------------------------------------------------

RECEIPT_PREFIX = "<!-- ideas-handoff: 1;"

REQUIRED_HEADINGS = (
    "## 1. Handoff",
    "## 2. Evidence",
    "## 3. Candidate ideas",
    "## 4. Comparison",
    "## 5. Recommendation",
    "## 6. Contradictions and open questions",
)
HANDOFF_STATES = {"decision-ready", "experiment-first", "research-limited"}
EXTERNAL_STATUSES = {"completed", "limited", "unavailable", "user-disabled", "local-only"}

CANDIDATE_ID_RE = re.compile(r"^### (I[1-7])\. ", re.MULTILINE)
CANDIDATE_ALL_RE = re.compile(r"^### (I\d+)\. ", re.MULTILINE)  # for counting
LOCAL_EVIDENCE_ID_RE = re.compile(r"^\| (L\d+) \|", re.MULTILINE)
EXTERNAL_EVIDENCE_ID_RE = re.compile(r"^\| (E\d+) \|", re.MULTILINE)
COMPARISON_RANK_RE = re.compile(r"^\| (\d+) \| (I[1-7]) \|", re.MULTILINE)
RECOMMENDATION_LEAD_RE = re.compile(r"^- Provisional lead:\s*(.+)$", re.MULTILINE)
EXTERNAL_STATUS_LINE_RE = re.compile(r"^External research status:\s*(.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^# Ideas: .+$", re.MULTILINE)
HANDOFF_STATE_RE = re.compile(r"^- State:\s*(.+)$", re.MULTILINE)
REQUIRED_CANDIDATE_FIELDS = (
    "Mechanism:",
    "Why it applies:",
    "Evidence:",
    "Expected impact:",
    "Effort:",
    "Risk:",
    "Confidence:",
    "What would disconfirm it:",
    "Cheapest decisive experiment:",
)
PROHIBITED_RE = re.compile(
    r"```(?:diff|patch)\s*\n(?:@@|\+\+\+|---)",
    re.IGNORECASE,
)
STRONG_VERIFICATION_RE = re.compile(
    r"\bverif(?:ied|ication confirmed)\b|\bconfirmed local\b|\bdirectly verified\b",
    re.IGNORECASE,
)

# Evidence reference in candidate blocks: E1, L2, etc.
EVIDENCE_REF_RE = re.compile(r"\b([EL]\d+)\b")

HANDOFF_REQUIRED_FIELDS = (
    "- Goal:",
    "- Scope:",
    "- Non-goals:",
    "- Assumptions:",
    "- Decision horizon:",
    "- Selected source playbooks:",
    "- Research coverage:",
    "- Research limitations:",
)

# ---------------------------------------------------------------------------
# Diagnostic dataclass
# ---------------------------------------------------------------------------


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
        path: str | Path = "ideas.md",
        next_command: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return normalize_diagnostic(
            asdict(self),
            skill="ideate",
            phase="validate",
            artifact="ideas",
            path=path,
            next_command=next_command,
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _section_body(text: str, heading: str) -> str:
    """Extract text from heading to next same-level heading or end."""
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


def _validate_id_sequence(
    ids: list[str],
    prefix: str,
    domain: str,
    dup_code: str,
    noncontig_code: str,
) -> list[Diagnostic]:
    """Validate uniqueness and contiguity for ID lists (e.g. L1.., E1.., I1..)."""
    errors: list[Diagnostic] = []
    if ids:
        nums = [int(item[len(prefix):]) for item in ids]
        if len(set(nums)) != len(nums):
            errors.append(Diagnostic(dup_code, f"{domain} IDs must be unique"))
        elif nums != list(range(1, len(nums) + 1)):
            errors.append(
                Diagnostic(
                    noncontig_code,
                    f"{domain} IDs must be contiguous starting at {prefix}1",
                )
            )
    return errors


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_ideas(text: str, repo_root: Path | None = None) -> list[Diagnostic]:
    """Validate an ideas.md body (receipt already stripped)."""
    errors: list[Diagnostic] = []

    # 1. Title
    if not TITLE_RE.search(text):
        errors.append(Diagnostic("ideas.missing_title", "document must begin with '# Ideas: <goal>'"))

    # 2. Required headings in order
    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        idx = text.find(heading)
        if idx == -1:
            errors.append(Diagnostic("ideas.missing_heading", f"required heading is absent: {heading!r}"))
            positions.append(-1)
        else:
            positions.append(idx)
    # Check order (ignore missing = -1)
    valid_positions = [p for p in positions if p != -1]
    if valid_positions != sorted(valid_positions):
        errors.append(Diagnostic("ideas.heading_order", "required headings must appear in canonical order"))

    # 3. Handoff section fields
    handoff_body = _section_body(text, "## 1. Handoff")
    for field in HANDOFF_REQUIRED_FIELDS:
        line_re = re.compile(rf"^{re.escape(field)}\s*\S", re.MULTILINE)
        if not line_re.search(handoff_body):
            errors.append(Diagnostic("ideas.handoff_field_empty", f"required handoff field is missing or empty: {field!r}"))

    # 4. Handoff state
    state_m = HANDOFF_STATE_RE.search(handoff_body)
    if not state_m:
        errors.append(Diagnostic("ideas.missing_state", "handoff '- State:' field is required"))
        state = ""
    else:
        state = state_m.group(1).strip()
        if state not in HANDOFF_STATES:
            errors.append(
                Diagnostic(
                    "ideas.invalid_state",
                    f"handoff state {state!r} must be one of: {', '.join(sorted(HANDOFF_STATES))}",
                )
            )

    # 5. External research status
    ext_status_m = EXTERNAL_STATUS_LINE_RE.search(text)
    if not ext_status_m:
        errors.append(Diagnostic("ideas.missing_external_status", "external research status line is required in Evidence section"))
        ext_status = ""
    else:
        ext_status = ext_status_m.group(1).strip()
        if ext_status not in EXTERNAL_STATUSES:
            errors.append(
                Diagnostic(
                    "ideas.invalid_external_status",
                    f"external research status {ext_status!r} must be one of: {', '.join(sorted(EXTERNAL_STATUSES))}",
                )
            )

    # 6. Collect declared evidence IDs
    declared_local: list[str] = LOCAL_EVIDENCE_ID_RE.findall(text)
    declared_external: list[str] = EXTERNAL_EVIDENCE_ID_RE.findall(text)

    # Check contiguity and uniqueness for local & external evidence
    errors.extend(
        _validate_id_sequence(
            declared_local,
            "L",
            "local evidence",
            "ideas.duplicate_local_evidence",
            "ideas.noncontiguous_local_evidence",
        )
    )
    errors.extend(
        _validate_id_sequence(
            declared_external,
            "E",
            "external evidence",
            "ideas.duplicate_external_evidence",
            "ideas.noncontiguous_external_evidence",
        )
    )

    # Validate local evidence rows: non-empty locator and verification
    evidence_section = _section_body(text, "## 2. Evidence")
    for row_m in re.finditer(
        r"^\| (L\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
        evidence_section,
        re.MULTILINE,
    ):
        lid, _claim, local_path, locator, verification = (
            row_m.group(1),
            row_m.group(2).strip(),
            row_m.group(3).strip(),
            row_m.group(4).strip(),
            row_m.group(5).strip(),
        )
        if not locator or locator in ("-", "—"):
            errors.append(Diagnostic("ideas.empty_local_locator", f"{lid}: locator must be non-empty"))
        if not verification or verification in ("-", "—"):
            errors.append(Diagnostic("ideas.empty_local_verification", f"{lid}: verification must be non-empty"))
        # Path escape check
        if repo_root is not None and local_path and local_path not in ("-", "—"):
            try:
                resolved = (repo_root / local_path).resolve()
                resolved.relative_to(repo_root.resolve())
            except ValueError:
                errors.append(Diagnostic("ideas.local_path_escape", f"{lid}: path {local_path!r} escapes the workspace root"))

    # 7. Candidate ideas
    candidate_ids = CANDIDATE_ID_RE.findall(text)  # valid I1-I7 matches
    all_candidate_refs = CANDIDATE_ALL_RE.findall(text)  # all I* for counting
    total_count = len(all_candidate_refs)
    if total_count < 3:
        errors.append(
            Diagnostic("ideas.too_few_candidates", f"at least 3 candidate ideas required, found {total_count}")
        )
    elif total_count > 7:
        errors.append(
            Diagnostic("ideas.too_many_candidates", f"at most 7 candidate ideas allowed, found {total_count}")
        )
    # Use valid-range IDs for further checks (when count in range)
    if total_count <= 7:
        errors.extend(
            _validate_id_sequence(
                candidate_ids,
                "I",
                "candidate",
                "ideas.duplicate_candidate_ids",
                "ideas.noncontiguous_candidate_ids",
            )
        )

    # 8. Each candidate must reference declared evidence and have required fields
    declared_all = set(declared_local) | set(declared_external)
    candidate_section = _section_body(text, "## 3. Candidate ideas")
    all_cited_evidence: set[str] = set()

    # Split into per-candidate blocks
    cand_blocks = re.split(r"(?=^### I[1-7]\. )", candidate_section, flags=re.MULTILINE)
    for block in cand_blocks:
        if not block.strip():
            continue
        cid_m = re.match(r"^### (I[1-7])\. ", block)
        if not cid_m:
            continue
        cid = cid_m.group(1)
        # Check required fields
        for field in REQUIRED_CANDIDATE_FIELDS:
            if f"- {field}" not in block:
                errors.append(Diagnostic("ideas.missing_candidate_field", f"{cid}: required field '- {field}' is absent"))
        # Check evidence references
        refs = set(EVIDENCE_REF_RE.findall(block))
        if declared_all and not refs:
            errors.append(
                Diagnostic(
                    "ideas.candidate_missing_evidence",
                    f"{cid}: candidate must reference at least one declared evidence ID",
                )
            )
        unknown = refs - declared_all
        for ref in sorted(unknown):
            errors.append(Diagnostic("ideas.unknown_evidence_reference", f"{cid}: references undeclared evidence {ref!r}"))
        all_cited_evidence.update(refs & declared_all)

    # Check for declared evidence that is never cited by any candidate
    uncited = declared_all - all_cited_evidence
    for uncited_id in sorted(uncited):
        errors.append(
            Diagnostic(
                "ideas.uncited_evidence",
                f"declared evidence {uncited_id!r} is never referenced by any candidate idea",
            )
        )

    # 9. Comparison table
    comparison_body = _section_body(text, "## 4. Comparison")
    comparison_rows = COMPARISON_RANK_RE.findall(comparison_body)  # [(rank, cid), ...]
    if comparison_rows:
        comp_ranks = [int(r) for r, _ in comparison_rows]
        comp_cids = [c for _, c in comparison_rows]
        # Ranks unique and contiguous
        if sorted(comp_ranks) != list(range(1, len(comp_ranks) + 1)):
            errors.append(Diagnostic("ideas.invalid_comparison_ranks", "comparison ranks must be unique and contiguous starting at 1"))
        # Every candidate appears exactly once
        if set(comp_cids) != set(candidate_ids):
            missing = sorted(set(candidate_ids) - set(comp_cids))
            extra = sorted(set(comp_cids) - set(candidate_ids))
            if missing:
                errors.append(Diagnostic("ideas.comparison_missing_candidate", f"comparison table is missing candidates: {missing}"))
            if extra:
                errors.append(Diagnostic("ideas.comparison_extra_candidate", f"comparison table contains unknown candidates: {extra}"))
        if len(comp_cids) != len(set(comp_cids)):
            errors.append(Diagnostic("ideas.comparison_duplicate_candidate", "each candidate must appear exactly once in the comparison table"))
    elif candidate_ids:
        errors.append(Diagnostic("ideas.missing_comparison_rows", "comparison table must rank all candidates"))

    # 10. Recommendation matches rank 1
    rec_body = _section_body(text, "## 5. Recommendation")
    lead_m = RECOMMENDATION_LEAD_RE.search(rec_body)
    if not lead_m:
        errors.append(Diagnostic("ideas.missing_recommendation_lead", "recommendation '- Provisional lead:' field is required"))
    elif comparison_rows:
        rank1 = next((c for r, c in comparison_rows if int(r) == 1), None)
        lead_text = lead_m.group(1).strip()
        if rank1 and rank1 not in lead_text:
            errors.append(
                Diagnostic(
                    "ideas.recommendation_mismatch",
                    f"provisional lead mentions {lead_text!r} but rank 1 is {rank1!r}",
                )
            )

    # 11. External status agreement with evidence
    if ext_status == "local-only" and declared_external:
        errors.append(
            Diagnostic("ideas.status_evidence_mismatch", "external status 'local-only' but external evidence rows are present")
        )
    if ext_status == "completed" and not declared_external:
        errors.append(
            Diagnostic("ideas.status_evidence_mismatch", "external status 'completed' but no external evidence rows found")
        )

    # 12. research-limited must not claim strong verification
    if state == "research-limited" and STRONG_VERIFICATION_RE.search(text):
        errors.append(
            Diagnostic(
                "ideas.limited_strong_verification",
                "state 'research-limited' must not claim strong verification of evidence",
            )
        )

    # 13. Prohibited implementation patches
    if PROHIBITED_RE.search(text):
        errors.append(
            Diagnostic(
                "ideas.prohibited_implementation",
                "ideas.md must not contain implementation patches or diff hunks",
            )
        )

    return errors


def validate_ideas_path(draft_path: Path, repo_root: Path | None = None) -> list[Diagnostic]:
    """Validate an ideas.md file on disk (strip receipt if present)."""
    text = draft_path.read_text(encoding="utf-8")
    # Strip receipt if present
    first, _, rest = text.partition("\n")
    if first.startswith("<!-- ideas-handoff:"):
        text = rest
    return validate_ideas(text, repo_root=repo_root)


def seal_body(text: str) -> str:
    """Normalize line endings and trailing whitespace for sealing."""
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def compute_digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
