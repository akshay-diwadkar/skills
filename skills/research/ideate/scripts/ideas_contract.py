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
OPTIONAL_HEADINGS = (
    "## 7. Optional downstream action",
)

HANDOFF_STATES = {"decision-ready", "experiment-first", "research-limited"}
EXTERNAL_STATUSES = {"completed", "limited", "unavailable", "user-disabled", "local-only"}

CANDIDATE_ID_RE = re.compile(r"^### (I[1-7])\.[ \t]*(.*)$", re.MULTILINE)
CANDIDATE_ALL_RE = re.compile(r"^### (I\d+)\.", re.MULTILINE)
LOCAL_EVIDENCE_ID_RE = re.compile(r"^\| (L\d+) \|", re.MULTILINE)
EXTERNAL_EVIDENCE_ID_RE = re.compile(r"^\| (E\d+) \|", re.MULTILINE)
COMPARISON_RANK_RE = re.compile(r"^\| (\d+) \| (I[1-7]) \|", re.MULTILINE)
RECOMMENDATION_LEAD_RE = re.compile(r"^- Provisional lead:[ \t]*(.+)$", re.MULTILINE)
EXTERNAL_STATUS_LINE_RE = re.compile(r"^External research status:[ \t]*(.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^# Ideas:[ \t]*(.+)$")
HANDOFF_STATE_RE = re.compile(r"^- State:[ \t]*(.+)$", re.MULTILINE)

HANDOFF_REQUIRED_FIELDS = (
    "- State:",
    "- Goal:",
    "- Success measure:",
    "- Baseline / status quo:",
    "- Scope:",
    "- Non-goals:",
    "- Assumptions:",
    "- Material unknowns:",
    "- Decision horizon:",
    "- Decision criteria:",
    "- Selected source playbooks:",
    "- Research coverage:",
    "- Research limitations:",
)

REQUIRED_CANDIDATE_FIELDS = (
    "Mechanism:",
    "Mechanism category:",
    "Why it applies:",
    "Evidence:",
    "Expected impact:",
    "Assumptions and dependencies:",
    "Effort:",
    "Risk:",
    "Confidence:",
    "What would disconfirm it:",
    "Cheapest decisive experiment:",
)

RECOMMENDATION_REQUIRED_FIELDS = (
    "- Provisional lead:",
    "- Why it leads:",
    "- Why it beats rank 2:",
    "- Cheapest decisive experiment:",
    "- What could change the ranking:",
    "- Conditions that would change the ranking:",
)

PROHIBITED_RE = re.compile(
    r"```(?:diff|patch)\s*\n(?:@@|\+\+\+|---)",
    re.IGNORECASE,
)
STRONG_VERIFICATION_RE = re.compile(
    r"\bverif(?:ied|ication confirmed)\b|\bconfirmed local\b|\bdirectly verified\b",
    re.IGNORECASE,
)

EVIDENCE_REF_RE = re.compile(r"\b([EL]\d+)\b")
DIGEST_RE = re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)

LOCAL_HEADER = "| ID | Claim | Source path | Locator | Verification |"
EXTERNAL_HEADER = "| ID | Finding | Source | Locator | Date/freshness | Relevance |"
COMPARISON_HEADER = "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |"

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

    # 1. Title is first non-empty body line with non-empty goal
    stripped_text = text.lstrip("\r\n")
    first_line = stripped_text.splitlines()[0].strip() if stripped_text else ""
    title_m = TITLE_RE.match(first_line)
    if not title_m or not title_m.group(1).strip():
        errors.append(Diagnostic("ideas.missing_title", "document must begin with '# Ideas: <goal>' on the first line"))

    # 2. Required headings in order and exactly once
    heading_positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        count = text.count(heading)
        if count == 0:
            errors.append(Diagnostic("ideas.missing_heading", f"required heading is absent: {heading!r}"))
            heading_positions.append(-1)
        elif count > 1:
            errors.append(Diagnostic("ideas.duplicate_heading", f"required heading appears {count} times: {heading!r}"))
            heading_positions.append(text.find(heading))
        else:
            heading_positions.append(text.find(heading))

    # Check order of present headings
    valid_positions = [p for p in heading_positions if p != -1]
    if valid_positions != sorted(valid_positions):
        errors.append(Diagnostic("ideas.heading_order", "required headings must appear in canonical order"))

    # Optional section 7 ordering
    sec7_idx = text.find("## 7. Optional downstream action")
    if sec7_idx != -1:
        if text.count("## 7. Optional downstream action") > 1:
            errors.append(Diagnostic("ideas.duplicate_heading", "optional heading '## 7. Optional downstream action' appears multiple times"))
        sec6_idx = text.find("## 6. Contradictions and open questions")
        if sec6_idx != -1 and sec7_idx < sec6_idx:
            errors.append(Diagnostic("ideas.heading_order", "Section 7 must appear after Section 6"))

    # 3. Handoff section fields
    handoff_body = _section_body(text, "## 1. Handoff")
    for field in HANDOFF_REQUIRED_FIELDS:
        line_re = re.compile(rf"^{re.escape(field)}[ \t]*(.*)$", re.MULTILINE)
        m = line_re.search(handoff_body)
        if not m or not m.group(1).strip():
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
    evidence_section = _section_body(text, "## 2. Evidence")
    ext_status_m = EXTERNAL_STATUS_LINE_RE.search(evidence_section)
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

    # 6. Collect declared evidence IDs and verify location
    declared_local: list[str] = LOCAL_EVIDENCE_ID_RE.findall(evidence_section)
    declared_external: list[str] = EXTERNAL_EVIDENCE_ID_RE.findall(evidence_section)

    all_doc_local = LOCAL_EVIDENCE_ID_RE.findall(text)
    all_doc_external = EXTERNAL_EVIDENCE_ID_RE.findall(text)

    if len(all_doc_local) > len(declared_local):
        errors.append(Diagnostic("ideas.misplaced_evidence_declaration", "local evidence IDs must be declared only inside Section 2"))
    if len(all_doc_external) > len(declared_external):
        errors.append(Diagnostic("ideas.misplaced_evidence_declaration", "external evidence IDs must be declared only inside Section 2"))

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

    # Evidence table headers and row widths
    if "### Local evidence" in evidence_section:
        if LOCAL_HEADER not in evidence_section:
            errors.append(Diagnostic("ideas.invalid_local_table_header", f"Local evidence table header must exactly match {LOCAL_HEADER!r}"))
    for line in evidence_section.splitlines():
        line_s = line.strip()
        if line_s.startswith("| L") and line_s.endswith("|"):
            parts = [p.strip() for p in line_s.split("|")[1:-1]]
            if len(parts) != 5:
                errors.append(Diagnostic("ideas.invalid_local_table_row_width", f"Local evidence row width must have 5 columns, found {len(parts)}"))

    if declared_external or "External research status:" in evidence_section:
        if EXTERNAL_HEADER not in evidence_section and declared_external:
            errors.append(Diagnostic("ideas.invalid_external_table_header", f"External evidence table header must exactly match {EXTERNAL_HEADER!r}"))
    for line in evidence_section.splitlines():
        line_s = line.strip()
        if line_s.startswith("| E") and line_s.endswith("|"):
            parts = [p.strip() for p in line_s.split("|")[1:-1]]
            if len(parts) != 6:
                errors.append(Diagnostic("ideas.invalid_external_table_row_width", f"External evidence row width must have 6 columns, found {len(parts)}"))

    # Validate local evidence rows: non-empty locator, verification, existence, hash-digest check
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
        elif "hash-verified" in verification.lower():
            if not DIGEST_RE.search(verification):
                errors.append(
                    Diagnostic("ideas.hash_verified_without_digest", f"{lid}: 'hash-verified' requires a SHA-256 digest")
                )

        # Path escape and file existence check
        if repo_root is not None and local_path and local_path not in ("-", "—"):
            try:
                resolved = (repo_root / local_path).resolve()
                resolved.relative_to(repo_root.resolve())
                if not resolved.exists() or not resolved.is_file():
                    errors.append(
                        Diagnostic("ideas.local_path_not_found", f"{lid}: path {local_path!r} does not exist or is not a regular file")
                    )
            except ValueError:
                errors.append(Diagnostic("ideas.local_path_escape", f"{lid}: path {local_path!r} escapes the workspace root"))

    # 7. Candidate ideas
    candidate_section = _section_body(text, "## 3. Candidate ideas")
    candidate_matches = CANDIDATE_ID_RE.findall(candidate_section)
    candidate_ids = [cid for cid, _ in candidate_matches]
    all_candidate_refs = CANDIDATE_ALL_RE.findall(candidate_section)
    total_count = len(all_candidate_refs)

    if total_count < 3:
        errors.append(
            Diagnostic("ideas.too_few_candidates", f"at least 3 candidate ideas required, found {total_count}")
        )
    elif total_count > 7:
        errors.append(
            Diagnostic("ideas.too_many_candidates", f"at most 7 candidate ideas allowed, found {total_count}")
        )

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

    # Validate candidate names and fields
    declared_all = set(declared_local) | set(declared_external)
    all_cited_evidence: set[str] = set()
    mechanism_categories: list[str] = []

    cand_blocks = re.split(r"(?=^### I[1-7]\. )", candidate_section, flags=re.MULTILINE)
    for block in cand_blocks:
        if not block.strip():
            continue
        cid_m = re.match(r"^### (I[1-7])\.[ \t]*(.*)$", block, re.MULTILINE)
        if not cid_m:
            continue
        cid = cid_m.group(1)
        cname = cid_m.group(2).strip()
        if not cname:
            errors.append(Diagnostic("ideas.empty_candidate_name", f"{cid}: candidate title/name must be non-empty"))

        # Check required candidate fields
        for field in REQUIRED_CANDIDATE_FIELDS:
            field_pattern = re.compile(rf"^- {re.escape(field)}[ \t]*(.*)$", re.MULTILINE)
            m = field_pattern.search(block)
            if not m or not m.group(1).strip():
                errors.append(Diagnostic("ideas.empty_candidate_field", f"{cid}: required field '- {field}' is empty"))

        # Collect Mechanism category for distinctness check
        cat_m = re.search(r"^- Mechanism category:[ \t]*(.+)$", block, re.MULTILINE)
        if cat_m and cat_m.group(1).strip():
            mechanism_categories.append(cat_m.group(1).strip().casefold())

        # Check evidence references strictly from candidate's '- Evidence:' field
        ev_field_m = re.search(r"^- Evidence:[ \t]*(.+)$", block, re.MULTILINE)
        if ev_field_m:
            ev_line_val = ev_field_m.group(1).strip()
            refs = set(EVIDENCE_REF_RE.findall(ev_line_val))
            if declared_all and not refs:
                errors.append(
                    Diagnostic(
                        "ideas.candidate_missing_evidence",
                        f"{cid}: candidate must reference at least one declared evidence ID in '- Evidence:' field",
                    )
                )
            unknown = refs - declared_all
            for ref in sorted(unknown):
                errors.append(Diagnostic("ideas.unknown_evidence_reference", f"{cid}: references undeclared evidence {ref!r}"))
            all_cited_evidence.update(refs & declared_all)
        elif declared_all:
            errors.append(
                Diagnostic(
                    "ideas.candidate_missing_evidence",
                    f"{cid}: candidate must reference at least one declared evidence ID",
                )
            )

    # Mechanism distinctness check
    if mechanism_categories and len(mechanism_categories) != len(set(mechanism_categories)):
        errors.append(
            Diagnostic("ideas.duplicate_mechanism_category", "candidates must be mechanism-distinct by Mechanism category")
        )

    # Uncited evidence check
    uncited = declared_all - all_cited_evidence
    for uncited_id in sorted(uncited):
        errors.append(
            Diagnostic(
                "ideas.uncited_evidence",
                f"declared evidence {uncited_id!r} is never referenced by any candidate idea",
            )
        )

    # 8. Comparison table
    comparison_body = _section_body(text, "## 4. Comparison")
    if comparison_body.strip():
        if COMPARISON_HEADER not in comparison_body:
            errors.append(Diagnostic("ideas.invalid_comparison_table_header", f"Comparison table header must exactly match {COMPARISON_HEADER!r}"))

    comparison_rows = COMPARISON_RANK_RE.findall(comparison_body)
    if comparison_rows:
        comp_ranks = [int(r) for r, _ in comparison_rows]
        comp_cids = [c for _, c in comparison_rows]
        if sorted(comp_ranks) != list(range(1, len(comp_ranks) + 1)):
            errors.append(Diagnostic("ideas.invalid_comparison_ranks", "comparison ranks must be unique and contiguous starting at 1"))
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

    for line in comparison_body.splitlines():
        line_s = line.strip()
        if line_s.startswith("| 1 |") or line_s.startswith("| 2 |") or line_s.startswith("| 3 |"):
            parts = [p.strip() for p in line_s.split("|")[1:-1]]
            if len(parts) != 7:
                errors.append(Diagnostic("ideas.invalid_comparison_table_row_width", f"Comparison row width must have 7 columns, found {len(parts)}"))

    # 9. Recommendation
    rec_body = _section_body(text, "## 5. Recommendation")
    for field in RECOMMENDATION_REQUIRED_FIELDS:
        field_pattern = re.compile(rf"^{re.escape(field)}[ \t]*(.*)$", re.MULTILINE)
        m = field_pattern.search(rec_body)
        if not m or not m.group(1).strip():
            errors.append(Diagnostic("ideas.missing_recommendation_field", f"required recommendation field is missing or empty: {field!r}"))

    lead_m = RECOMMENDATION_LEAD_RE.search(rec_body)
    if lead_m and comparison_rows:
        rank1 = next((c for r, c in comparison_rows if int(r) == 1), None)
        lead_text = lead_m.group(1).strip()
        if rank1 and rank1 not in lead_text:
            errors.append(
                Diagnostic(
                    "ideas.recommendation_mismatch",
                    f"provisional lead mentions {lead_text!r} but rank 1 is {rank1!r}",
                )
            )

    # 10. External status agreement with evidence & State coherence
    if ext_status == "local-only" and declared_external:
        errors.append(
            Diagnostic("ideas.status_evidence_mismatch", "external status 'local-only' but external evidence rows are present")
        )
    if ext_status == "completed" and not declared_external:
        errors.append(
            Diagnostic("ideas.status_evidence_mismatch", "external status 'completed' but no external evidence rows found")
        )
    if state == "research-limited" and ext_status == "completed":
        errors.append(
            Diagnostic("ideas.incoherent_state_status", "handoff state 'research-limited' is incoherent with external status 'completed'")
        )

    # 11. research-limited restriction (applies to external evidence / findings, not local facts)
    if state == "research-limited":
        ext_evidence_text = ""
        ext_m = re.search(r"### External evidence.*?(?=### |\Z)", evidence_section, re.DOTALL)
        if ext_m:
            ext_evidence_text = ext_m.group(0)
        if STRONG_VERIFICATION_RE.search(ext_evidence_text):
            errors.append(
                Diagnostic(
                    "ideas.limited_strong_verification",
                    "state 'research-limited' must not claim strong verification of external evidence",
                )
            )

    # 12. Section 7 routing restriction
    sec7_body = _section_body(text, "## 7. Optional downstream action")
    if sec7_body and "implement-plan" in sec7_body.lower():
        errors.append(
            Diagnostic(
                "ideas.prohibited_direct_implementation",
                "optional downstream action must never route directly to 'implement-plan'",
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
    first, _, rest = text.partition("\n")
    if first.startswith("<!-- ideas-handoff:"):
        text = rest
    return validate_ideas(text, repo_root=repo_root)


def seal_body(text: str) -> str:
    """Normalize line endings and trailing whitespace for sealing."""
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def compute_digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
