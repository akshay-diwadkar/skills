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

RECEIPT_PREFIX = "<!-- ideas-handoff: 2;"

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
CONTEXTUAL_ORIGINS = {"user-provided", "direct observation", "prior attempt", "general knowledge"}
RESEARCH_STOP_REASONS = ("condition met", "diminishing returns", "unavailable sources", "user limit")

CANDIDATE_ID_RE = re.compile(r"^### (I[1-7])\. (.*)$", re.MULTILINE)
CANDIDATE_HEADING_RE = re.compile(r"^###+.*$", re.MULTILINE)
LOCAL_EVIDENCE_ID_RE = re.compile(r"^\| (L\d+) \|", re.MULTILINE)
EXTERNAL_EVIDENCE_ID_RE = re.compile(r"^\| (E\d+) \|", re.MULTILINE)
CONTEXTUAL_EVIDENCE_ID_RE = re.compile(r"^\| (C\d+) \|", re.MULTILINE)
COMPARISON_RANK_RE = re.compile(r"^\| (\d+) \| (I[1-7]) \|", re.MULTILINE)
RECOMMENDATION_LEAD_RE = re.compile(r"^- Provisional lead:[ \t]*(.+)$", re.MULTILINE)
RECOMMENDATION_LEAD_ID_RE = re.compile(r"^- Provisional lead:[ \t]*I([1-7])\b", re.MULTILINE)
EXTERNAL_STATUS_LINE_RE = re.compile(r"^External research status:[ \t]*(.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^# Ideas:[ \t]*(.+)$")
HANDOFF_STATE_RE = re.compile(r"^- State:[ \t]*(.+)$", re.MULTILINE)
RESEARCH_STOP_REASON_RE = re.compile(r"^- Research stop reason:[ \t]*(.+)$", re.MULTILINE)
SUPPORT_BASIS_LINE_RE = re.compile(r"^- Support basis:[ \t]*(.*)$", re.MULTILINE)
SUPPORT_BASIS_RE = re.compile(
    r"^- Support basis:[ \t]*(evidence-backed|assumption-backed|hypothesis)(?:[ \t]*:[ \t]*(.*))?$",
    re.MULTILINE,
)

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
    "- Research stop condition:",
    "- Research stop reason:",
)

REQUIRED_CANDIDATE_FIELDS = (
    "Mechanism:",
    "Mechanism category:",
    "Why it applies:",
    "Evidence:",
    "Support basis:",
    "Decision-criteria fit:",
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
    "- How decision criteria were applied:",
)

SECTION6_REQUIRED_FIELDS = (
    "- Strongest challenge to rank 1:",
    "- Baseline / status quo comparison:",
    "- Condition for a different winner:",
    "- Remaining contradiction or uncertainty:",
)

PROHIBITED_RE = re.compile(
    r"```(?:diff|patch)\s*\n(?:@@|\+\+\+|---)",
    re.IGNORECASE,
)
STRONG_VERIFICATION_RE = re.compile(
    r"\bverif(?:ied|ication confirmed)\b|\bconfirmed local\b|\bdirectly verified\b",
    re.IGNORECASE,
)

EVIDENCE_REF_RE = re.compile(r"\b([CEL]\d+)\b")
DIGEST_RE = re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)

LOCAL_HEADER = "| ID | Claim | Source path | Locator | Verification |"
EXTERNAL_HEADER = "| ID | Finding | Source | Locator | Date/freshness | Relevance |"
COMPARISON_HEADER = "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |"
CONTEXTUAL_HEADER = "| ID | Claim | Origin | Verification |"

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


EXPERIMENT_COMPONENT_RE = re.compile(
    r"(metric|pass/fail|duration|cost/effort|cost|effort)\s*:\s*([^;]*)",
    re.IGNORECASE,
)
REQUIRED_EXPERIMENT_COMPONENTS = ("metric", "pass/fail", "duration")
COST_EFFORT_COMPONENTS = ("cost/effort", "cost", "effort")


def _parse_experiment_components(value: str) -> dict[str, str]:
    """Parse 'metric: m; pass/fail: p; ...' into component name -> trimmed value."""
    components: dict[str, str] = {}
    for m in EXPERIMENT_COMPONENT_RE.finditer(value):
        name = m.group(1).lower()
        components[name] = m.group(2).strip()
    return components


def _validate_decisive_experiment(owner: str, value: str) -> list[Diagnostic]:
    """Require a metric, pass/fail rule, duration bound, and cost/effort bound.

    Each component must be present with a non-empty value; a bare label such
    as 'metric:' does not satisfy the contract.
    """
    errors: list[Diagnostic] = []
    components = _parse_experiment_components(value)
    for name in REQUIRED_EXPERIMENT_COMPONENTS:
        if not components.get(name, ""):
            errors.append(
                Diagnostic(
                    "ideas.decisive_experiment_incomplete",
                    f"{owner}: decisive experiment requires a non-empty '{name}:' value",
                )
            )
    if not any(components.get(name, "") for name in COST_EFFORT_COMPONENTS):
        errors.append(
            Diagnostic(
                "ideas.decisive_experiment_incomplete",
                f"{owner}: decisive experiment requires a non-empty 'cost:' or 'effort:' bound",
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

    # 5. Research stop reason vocabulary
    stop_reason_m = RESEARCH_STOP_REASON_RE.search(handoff_body)
    if stop_reason_m and stop_reason_m.group(1).strip():
        stop_value = stop_reason_m.group(1).strip()
        stop_lowered = stop_value.casefold()
        if not any(stop_lowered.startswith(reason) for reason in RESEARCH_STOP_REASONS):
            errors.append(
                Diagnostic(
                    "ideas.invalid_research_stop_reason",
                    f"research stop reason {stop_value!r} must begin with one of: {', '.join(RESEARCH_STOP_REASONS)}",
                )
            )

    # 6. External research status
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

    # 7. Collect declared evidence IDs and verify location
    declared_local: list[str] = LOCAL_EVIDENCE_ID_RE.findall(evidence_section)
    declared_external: list[str] = EXTERNAL_EVIDENCE_ID_RE.findall(evidence_section)
    declared_contextual: list[str] = CONTEXTUAL_EVIDENCE_ID_RE.findall(evidence_section)

    all_doc_local = LOCAL_EVIDENCE_ID_RE.findall(text)
    all_doc_external = EXTERNAL_EVIDENCE_ID_RE.findall(text)
    all_doc_contextual = CONTEXTUAL_EVIDENCE_ID_RE.findall(text)

    if len(all_doc_local) > len(declared_local):
        errors.append(Diagnostic("ideas.misplaced_evidence_declaration", "local evidence IDs must be declared only inside Section 2"))
    if len(all_doc_external) > len(declared_external):
        errors.append(Diagnostic("ideas.misplaced_evidence_declaration", "external evidence IDs must be declared only inside Section 2"))
    if len(all_doc_contextual) > len(declared_contextual):
        errors.append(Diagnostic("ideas.misplaced_evidence_declaration", "contextual evidence IDs must be declared only inside Section 2"))

    # Check contiguity and uniqueness for local, external, and contextual evidence
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
    errors.extend(
        _validate_id_sequence(
            declared_contextual,
            "C",
            "contextual evidence",
            "ideas.duplicate_contextual_evidence",
            "ideas.noncontiguous_contextual_evidence",
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

    # Contextual evidence table header, row widths, and row content
    if "### Contextual evidence" in evidence_section:
        if CONTEXTUAL_HEADER not in evidence_section:
            errors.append(Diagnostic("ideas.invalid_contextual_table_header", f"Contextual evidence table header must exactly match {CONTEXTUAL_HEADER!r}"))
    for line in evidence_section.splitlines():
        line_s = line.strip()
        if line_s.startswith("| C") and line_s.endswith("|"):
            parts = [p.strip() for p in line_s.split("|")[1:-1]]
            if len(parts) != 4:
                errors.append(Diagnostic("ideas.invalid_contextual_table_row_width", f"Contextual evidence row width must have 4 columns, found {len(parts)}"))
    for row_m in re.finditer(
        r"^\| (C\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
        evidence_section,
        re.MULTILINE,
    ):
        cid, c_claim, c_origin, c_verification = (
            row_m.group(1),
            row_m.group(2).strip(),
            row_m.group(3).strip(),
            row_m.group(4).strip(),
        )
        if not c_claim or c_claim in ("-", "â€”"):
            errors.append(Diagnostic("ideas.empty_contextual_claim", f"{cid}: claim must be non-empty"))
        if c_origin.casefold() not in CONTEXTUAL_ORIGINS:
            errors.append(
                Diagnostic(
                    "ideas.invalid_contextual_origin",
                    f"{cid}: origin {c_origin!r} must be one of: {', '.join(sorted(CONTEXTUAL_ORIGINS))}",
                )
            )
        if not c_verification or c_verification in ("-", "â€”"):
            errors.append(Diagnostic("ideas.empty_contextual_verification", f"{cid}: verification must be non-empty"))

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
        if not locator or locator in ("-", "â€”"):
            errors.append(Diagnostic("ideas.empty_local_locator", f"{lid}: locator must be non-empty"))
        if not verification or verification in ("-", "â€”"):
            errors.append(Diagnostic("ideas.empty_local_verification", f"{lid}: verification must be non-empty"))

        # Path escape and file existence check
        resolved = None
        if repo_root is not None and local_path and local_path not in ("-", "â€”"):
            try:
                resolved = (repo_root / local_path).resolve()
                resolved.relative_to(repo_root.resolve())
                if not resolved.exists() or not resolved.is_file():
                    errors.append(
                        Diagnostic("ideas.local_path_not_found", f"{lid}: path {local_path!r} does not exist or is not a regular file")
                    )
                    resolved = None
            except ValueError:
                resolved = None
                errors.append(Diagnostic("ideas.local_path_escape", f"{lid}: path {local_path!r} escapes the workspace root"))

        # hash-verified: digest must be present and match the referenced file
        if "hash-verified" in verification.lower():
            digest_m = DIGEST_RE.search(verification)
            if not digest_m:
                errors.append(
                    Diagnostic("ideas.hash_verified_without_digest", f"{lid}: 'hash-verified' requires a SHA-256 digest")
                )
            elif resolved is not None:
                actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
                if digest_m.group(0).lower() != actual:
                    errors.append(
                        Diagnostic(
                            "ideas.hash_verified_digest_mismatch",
                            f"{lid}: 'hash-verified' digest does not match file {local_path!r}",
                        )
                    )

    # 8. Candidate ideas
    candidate_section = _section_body(text, "## 3. Candidate ideas")
    candidate_matches = CANDIDATE_ID_RE.findall(candidate_section)
    candidate_ids = [cid for cid, _ in candidate_matches]
    total_count = len(candidate_ids)

    # Reject headings in Section 3 that are not canonical '### I1..I7. <name>'
    for heading_line in CANDIDATE_HEADING_RE.findall(candidate_section):
        if not CANDIDATE_ID_RE.match(heading_line):
            errors.append(
                Diagnostic(
                    "ideas.noncanonical_candidate_heading",
                    f"candidate heading {heading_line.strip()!r} must match '### I1..I7. <name>'",
                )
            )

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
    declared_all = set(declared_local) | set(declared_external) | set(declared_contextual)
    all_cited_evidence: set[str] = set()
    mechanism_categories: list[str] = []
    support_labels: list[str] = []

    cand_blocks = re.split(r"(?=^### I[1-7]\. )", candidate_section, flags=re.MULTILINE)
    for block in cand_blocks:
        if not block.strip():
            continue
        cid_m = CANDIDATE_ID_RE.match(block)
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

        # Check decisive experiment subfields
        exp_m = re.search(r"^- Cheapest decisive experiment:[ \t]*(.+)$", block, re.MULTILINE)
        if exp_m:
            errors.extend(_validate_decisive_experiment(cid, exp_m.group(1)))

        # Collect Mechanism category for distinctness check
        cat_m = re.search(r"^- Mechanism category:[ \t]*(.+)$", block, re.MULTILINE)
        if cat_m and cat_m.group(1).strip():
            mechanism_categories.append(cat_m.group(1).strip().casefold())

        # Check support basis: single machine-parsed support declaration
        sb_line_m = SUPPORT_BASIS_LINE_RE.search(block)
        sb_m = SUPPORT_BASIS_RE.search(block)
        if sb_line_m and sb_line_m.group(1).strip() and not sb_m:
            errors.append(
                Diagnostic(
                    "ideas.invalid_support_basis",
                    f"{cid}: support basis must be 'evidence-backed: <IDs>', 'assumption-backed: <assumption>', or 'hypothesis'",
                )
            )
        elif sb_m:
            label = sb_m.group(1).strip().casefold()
            qualifier = (sb_m.group(2) or "").strip()
            support_labels.append(label)
            if label == "evidence-backed":
                refs = set(EVIDENCE_REF_RE.findall(qualifier))
                if not refs:
                    errors.append(
                        Diagnostic(
                            "ideas.evidence_backed_without_refs",
                            f"{cid}: support basis 'evidence-backed' requires at least one declared evidence ID (L/E/C)",
                        )
                    )
                unknown = refs - declared_all
                for ref in sorted(unknown):
                    errors.append(Diagnostic("ideas.unknown_evidence_reference", f"{cid}: references undeclared evidence {ref!r}"))
                all_cited_evidence.update(refs & declared_all)
            elif label == "assumption-backed":
                if not qualifier:
                    errors.append(
                        Diagnostic(
                            "ideas.invalid_support_basis",
                            f"{cid}: support basis 'assumption-backed' must identify the material assumption",
                        )
                    )
            else:  # hypothesis
                if qualifier:
                    errors.append(
                        Diagnostic(
                            "ideas.invalid_support_basis",
                            f"{cid}: support basis 'hypothesis' must be a bare label",
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

    # State coherence: decision-ready cannot rely solely on unsupported hypotheses
    if state == "decision-ready" and support_labels and not any(
        label in ("evidence-backed", "assumption-backed") for label in support_labels
    ):
        errors.append(
            Diagnostic(
                "ideas.unsupported_decision_ready",
                "handoff state 'decision-ready' requires at least one evidence-backed or assumption-backed candidate",
            )
        )

    # 9. Comparison table
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

    comparison_row_re = re.compile(r"^\| ?\d+ ?\|")
    for line in comparison_body.splitlines():
        line_s = line.strip()
        if comparison_row_re.match(line_s):
            parts = [p.strip() for p in line_s.split("|")[1:-1]]
            if len(parts) != 7:
                errors.append(Diagnostic("ideas.invalid_comparison_table_row_width", f"Comparison row width must have 7 columns, found {len(parts)}"))

    # 10. Recommendation
    rec_body = _section_body(text, "## 5. Recommendation")
    for field in RECOMMENDATION_REQUIRED_FIELDS:
        field_pattern = re.compile(rf"^{re.escape(field)}[ \t]*(.*)$", re.MULTILINE)
        m = field_pattern.search(rec_body)
        if not m or not m.group(1).strip():
            errors.append(Diagnostic("ideas.missing_recommendation_field", f"required recommendation field is missing or empty: {field!r}"))

    lead_m = RECOMMENDATION_LEAD_RE.search(rec_body)
    if lead_m and comparison_rows:
        rank1 = next((c for r, c in comparison_rows if int(r) == 1), None)
        lead_id_m = RECOMMENDATION_LEAD_ID_RE.search(rec_body)
        lead_id = "I" + lead_id_m.group(1) if lead_id_m else None
        if rank1 and lead_id != rank1:
            errors.append(
                Diagnostic(
                    "ideas.recommendation_mismatch",
                    f"provisional lead must parse exactly to {rank1!r}, found {lead_id!r}",
                )
            )

    rec_exp_m = re.search(r"^- Cheapest decisive experiment:[ \t]*(.+)$", rec_body, re.MULTILINE)
    if rec_exp_m:
        errors.extend(_validate_decisive_experiment("recommendation", rec_exp_m.group(1)))

    # 11. External status agreement with evidence & State coherence
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

    # 12. research-limited restriction (applies to external evidence / findings, not local facts)
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

    # 13. Section 7 routing restriction
    sec7_body = _section_body(text, "## 7. Optional downstream action")
    if sec7_body and "implement-plan" in sec7_body.lower():
        errors.append(
            Diagnostic(
                "ideas.prohibited_direct_implementation",
                "optional downstream action must never route directly to 'implement-plan'",
            )
        )

    # 14. Prohibited implementation patches
    if PROHIBITED_RE.search(text):
        errors.append(
            Diagnostic(
                "ideas.prohibited_implementation",
                "ideas.md must not contain implementation patches or diff hunks",
            )
        )

    # 15. Section 6 non-emptiness and required challenge fields
    sec6_body = _section_body(text, "## 6. Contradictions and open questions")
    if not sec6_body.strip():
        errors.append(
            Diagnostic(
                "ideas.empty_section6",
                "Section 6 (Contradictions and open questions) must be non-empty",
            )
        )
    for field in SECTION6_REQUIRED_FIELDS:
        field_pattern = re.compile(rf"^{re.escape(field)}[ \t]*(.*)$", re.MULTILINE)
        m = field_pattern.search(sec6_body)
        if not m or not m.group(1).strip():
            errors.append(
                Diagnostic(
                    "ideas.empty_section6_field",
                    f"required Section 6 field is missing or empty: {field!r}",
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
