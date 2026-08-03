from __future__ import annotations

import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "research" / "ideate"
sys.path.insert(0, str(SKILL / "scripts"))

from ideas_contract import validate_ideas  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal valid bodies for reuse
# ---------------------------------------------------------------------------


def _valid_body(
    state: str = "decision-ready",
    ext_status: str = "completed",
    local_rows: str = "",
    ext_rows: str = "| E1 | Found X | https://example.com | \u00a7 2 | 2026-07 | high |\n",
    candidates: str | None = None,
    comparison: str | None = None,
    lead: str = "I1",
    rec_lead: str | None = None,
) -> str:
    # When no external evidence rows, candidates must not reference E1
    has_ext = bool(ext_rows)
    if candidates is None:
        ev_ref = "E1" if has_ext else "(none)"
        candidates = (
            "### I1. Alpha\n"
            f"- Mechanism: do X\n- Why it applies: because Y\n- Evidence: {ev_ref}\n"
            "- Expected impact: high\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
            "- Cheapest decisive experiment: try Z\n\n"
            "### I2. Beta\n"
            f"- Mechanism: do Y\n- Why it applies: because Z\n- Evidence: {ev_ref}\n"
            "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A fails\n"
            "- Cheapest decisive experiment: try A\n\n"
            "### I3. Gamma\n"
            f"- Mechanism: do Z\n- Why it applies: because W\n- Evidence: {ev_ref}\n"
            "- Expected impact: low\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B fails\n"
            "- Cheapest decisive experiment: try B\n\n"
        )
    if comparison is None:
        comparison = (
            "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 1 | {lead} | high | low | low | moderate | strong |\n"
            "| 2 | I2 | medium | medium | medium | low | moderate |\n"
            "| 3 | I3 | low | high | high | low | weak |\n"
        )
    local_section = ""
    if local_rows:
        local_section = (
            "### Local evidence\n\n"
            "| ID | Claim | Source path | Locator | Verification |\n"
            "| --- | --- | --- | --- | --- |\n"
            + local_rows
            + "\n"
        )
    ext_table = ""
    if ext_rows:
        ext_table = (
            "| ID | Finding | Source | Locator | Date/freshness | Relevance |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            + ext_rows
        )
    # rec_lead defaults to lead (same as rank-1 comparison candidate)
    actual_rec_lead = rec_lead if rec_lead is not None else lead
    return (
        f"# Ideas: reduce latency\n\n"
        f"## 1. Handoff\n"
        f"- State: {state}\n"
        f"- Goal: reduce latency\n"
        f"- Scope: API layer\n"
        f"- Non-goals: database\n"
        f"- Assumptions: current p99 = 500 ms\n"
        f"- Decision horizon: Q3 2026\n"
        f"- Selected source playbooks: software/engineering\n"
        f"- Research coverage: docs, benchmarks\n"
        f"- Research limitations: none\n\n"
        f"## 2. Evidence\n\n"
        + local_section
        + "### External evidence\n\n"
        + f"External research status: {ext_status}\n\n"
        + ext_table
        + "\n## 3. Candidate ideas\n\n"
        + candidates
        + "## 4. Comparison\n\n"
        + comparison
        + "\n## 5. Recommendation\n"
        + f"- Provisional lead: {actual_rec_lead} \u2014 Alpha\n"
        + "- Why it leads: best ratio\n"
        + "- Cheapest decisive experiment: try Z\n"
        + "- What could change the ranking: new evidence\n\n"
        "## 6. Contradictions and open questions\n"
        "- None identified.\n"
    )


# ---------------------------------------------------------------------------
# Valid cases
# ---------------------------------------------------------------------------


def test_valid_external_only() -> None:
    assert validate_ideas(_valid_body()) == []


def test_valid_with_local_evidence(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    body = _valid_body(
        local_rows="| L1 | owns latency | src/app.py | line 1: # app | hash-verified |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Why it applies: because Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
            "- Cheapest decisive experiment: try Z\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Why it applies: because Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A fails\n"
            "- Cheapest decisive experiment: try A\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Why it applies: because W\n- Evidence: L1\n"
            "- Expected impact: low\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B fails\n"
            "- Cheapest decisive experiment: try B\n\n"
        ),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_valid_local_only() -> None:
    body = _valid_body(ext_status="local-only", ext_rows="")
    assert validate_ideas(body) == []


def test_all_external_statuses() -> None:
    for status in ("completed", "limited", "unavailable", "user-disabled", "local-only"):
        ext_rows = "| E1 | Found X | https://example.com | \u00a7 2 | 2026-07 | high |\n" if status != "local-only" else ""
        body = _valid_body(ext_status=status, ext_rows=ext_rows)
        errors = validate_ideas(body)
        assert errors == [], f"status={status!r}: {errors}"


def test_valid_seven_candidates() -> None:
    cands = ""
    comp_rows = ""
    for i in range(1, 8):
        cands += (
            f"### I{i}. Option{i}\n"
            f"- Mechanism: M{i}\n- Why it applies: W{i}\n- Evidence: E1\n"
            f"- Expected impact: low\n- Effort: low\n- Risk: low\n"
            f"- Confidence: low\n- What would disconfirm it: D{i}\n"
            f"- Cheapest decisive experiment: V{i}\n\n"
        )
        rank = i
        comp_rows += f"| {rank} | I{i} | low | low | low | low | weak |\n"
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        + comp_rows
    )
    body = _valid_body(candidates=cands, comparison=comparison, lead="I1")
    assert validate_ideas(body) == []


# ---------------------------------------------------------------------------
# Missing / reordered headings
# ---------------------------------------------------------------------------


def test_missing_required_heading() -> None:
    body = _valid_body().replace("## 4. Comparison", "## 4. Broken")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_heading" in codes or "ideas.heading_order" in codes


def test_reordered_headings() -> None:
    # Swap sections 3 and 4
    body = _valid_body()
    cand_start = body.index("## 3. Candidate ideas")
    comp_start = body.index("## 4. Comparison")
    rec_start = body.index("## 5. Recommendation")
    candidates_block = body[cand_start:comp_start]
    comparison_block = body[comp_start:rec_start]
    reordered = body[:cand_start] + comparison_block + candidates_block + body[rec_start:]
    codes = [e.code for e in validate_ideas(reordered)]
    assert "ideas.heading_order" in codes


# ---------------------------------------------------------------------------
# Handoff state
# ---------------------------------------------------------------------------


def test_invalid_handoff_state() -> None:
    body = _valid_body(state="unknown-state")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_state" in codes


# ---------------------------------------------------------------------------
# Candidate count
# ---------------------------------------------------------------------------


def test_fewer_than_3_candidates() -> None:
    cands = (
        "### I1. Alpha\n"
        "- Mechanism: do X\n- Why it applies: because Y\n- Evidence: E1\n"
        "- Expected impact: high\n- Effort: low\n- Risk: low\n"
        "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
        "- Cheapest decisive experiment: try Z\n\n"
        "### I2. Beta\n"
        "- Mechanism: do Y\n- Why it applies: because Z\n- Evidence: E1\n"
        "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
        "- Confidence: low\n- What would disconfirm it: A fails\n"
        "- Cheapest decisive experiment: try A\n\n"
    )
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | medium | low | moderate |\n"
    )
    body = _valid_body(candidates=cands, comparison=comparison)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.too_few_candidates" in codes


def test_more_than_7_candidates() -> None:
    cands = ""
    comp_rows = ""
    for i in range(1, 9):  # 8 candidates
        cands += (
            f"### I{i}. Option{i}\n"
            f"- Mechanism: M{i}\n- Why it applies: W{i}\n- Evidence: E1\n"
            f"- Expected impact: low\n- Effort: low\n- Risk: low\n"
            f"- Confidence: low\n- What would disconfirm it: D{i}\n"
            f"- Cheapest decisive experiment: V{i}\n\n"
        )
        comp_rows += f"| {i} | I{i} | low | low | low | low | weak |\n"
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        + comp_rows
    )
    body = _valid_body(candidates=cands, comparison=comparison, lead="I1")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.too_many_candidates" in codes


# ---------------------------------------------------------------------------
# Candidate IDs
# ---------------------------------------------------------------------------


def test_duplicate_candidate_ids() -> None:
    cands = (
        "### I1. Alpha\n"
        "- Mechanism: do X\n- Why it applies: because Y\n- Evidence: E1\n"
        "- Expected impact: high\n- Effort: low\n- Risk: low\n"
        "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
        "- Cheapest decisive experiment: try Z\n\n"
        "### I1. AlphaDupe\n"
        "- Mechanism: do Y\n- Why it applies: because Z\n- Evidence: E1\n"
        "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
        "- Confidence: low\n- What would disconfirm it: A fails\n"
        "- Cheapest decisive experiment: try A\n\n"
        "### I3. Gamma\n"
        "- Mechanism: do Z\n- Why it applies: because W\n- Evidence: E1\n"
        "- Expected impact: low\n- Effort: high\n- Risk: high\n"
        "- Confidence: low\n- What would disconfirm it: B fails\n"
        "- Cheapest decisive experiment: try B\n\n"
    )
    body = _valid_body(candidates=cands)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.duplicate_candidate_ids" in codes or "ideas.noncontiguous_candidate_ids" in codes


def test_noncontinuous_candidate_ids() -> None:
    # I1, I3 — skips I2
    cands = (
        "### I1. Alpha\n"
        "- Mechanism: do X\n- Why it applies: because Y\n- Evidence: E1\n"
        "- Expected impact: high\n- Effort: low\n- Risk: low\n"
        "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
        "- Cheapest decisive experiment: try Z\n\n"
        "### I3. Gamma\n"
        "- Mechanism: do Z\n- Why it applies: because W\n- Evidence: E1\n"
        "- Expected impact: low\n- Effort: high\n- Risk: high\n"
        "- Confidence: low\n- What would disconfirm it: B fails\n"
        "- Cheapest decisive experiment: try B\n\n"
        "### I4. Delta\n"
        "- Mechanism: do W\n- Why it applies: because V\n- Evidence: E1\n"
        "- Expected impact: low\n- Effort: low\n- Risk: low\n"
        "- Confidence: low\n- What would disconfirm it: C fails\n"
        "- Cheapest decisive experiment: try C\n\n"
    )
    body = _valid_body(candidates=cands)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncontiguous_candidate_ids" in codes


# ---------------------------------------------------------------------------
# Evidence IDs
# ---------------------------------------------------------------------------


def test_duplicate_external_evidence_ids() -> None:
    ext_rows = (
        "| E1 | Finding A | https://a.com | § 1 | 2026-07 | high |\n"
        "| E1 | Finding B | https://b.com | § 2 | 2026-07 | medium |\n"
    )
    body = _valid_body(ext_rows=ext_rows)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.duplicate_external_evidence" in codes


def test_noncontiguous_external_evidence_ids() -> None:
    ext_rows = (
        "| E1 | Finding A | https://a.com | § 1 | 2026-07 | high |\n"
        "| E3 | Finding C | https://c.com | § 3 | 2026-07 | low |\n"
    )
    body = _valid_body(ext_rows=ext_rows)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncontiguous_external_evidence" in codes


def test_unknown_evidence_reference() -> None:
    # Candidate references E9 which is not declared
    cands = (
        "### I1. Alpha\n"
        "- Mechanism: do X\n- Why it applies: because Y\n- Evidence: E1, E9\n"
        "- Expected impact: high\n- Effort: low\n- Risk: low\n"
        "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
        "- Cheapest decisive experiment: try Z\n\n"
        "### I2. Beta\n"
        "- Mechanism: do Y\n- Why it applies: because Z\n- Evidence: E1\n"
        "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
        "- Confidence: low\n- What would disconfirm it: A fails\n"
        "- Cheapest decisive experiment: try A\n\n"
        "### I3. Gamma\n"
        "- Mechanism: do Z\n- Why it applies: because W\n- Evidence: E1\n"
        "- Expected impact: low\n- Effort: high\n- Risk: high\n"
        "- Confidence: low\n- What would disconfirm it: B fails\n"
        "- Cheapest decisive experiment: try B\n\n"
    )
    body = _valid_body(candidates=cands)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.unknown_evidence_reference" in codes


# ---------------------------------------------------------------------------
# Local evidence path
# ---------------------------------------------------------------------------


def test_local_path_escape(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app", encoding="utf-8")
    body = _valid_body(
        local_rows="| L1 | claim | ../../etc/passwd | line 1: root | hash-verified |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B\n\n"
        ),
    )
    codes = [e.code for e in validate_ideas(body, repo_root=tmp_path)]
    assert "ideas.local_path_escape" in codes


def test_missing_local_locator() -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | - | hash-verified |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B\n\n"
        ),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_local_locator" in codes


def test_missing_local_verification() -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1: foo | - |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B\n\n"
        ),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_local_verification" in codes


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------


def test_comparison_missing_candidate() -> None:
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | medium | low | moderate |\n"
        # I3 missing
    )
    body = _valid_body(comparison=comparison)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.comparison_missing_candidate" in codes


def test_comparison_duplicate_candidate() -> None:
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I1 | high | low | low | moderate | strong |\n"
        "| 3 | I3 | low | high | high | low | weak |\n"
    )
    body = _valid_body(comparison=comparison)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.comparison_duplicate_candidate" in codes or "ideas.comparison_missing_candidate" in codes


def test_invalid_comparison_ranks() -> None:
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 3 | I2 | medium | medium | medium | low | moderate |\n"
        "| 5 | I3 | low | high | high | low | weak |\n"
    )
    body = _valid_body(comparison=comparison)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_comparison_ranks" in codes


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def test_recommendation_mismatch() -> None:
    # Comparison rank 1 = I1, but recommendation lead says I2 — should be a mismatch
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | medium | low | moderate |\n"
        "| 3 | I3 | low | high | high | low | weak |\n"
    )
    body = _valid_body(lead="I1", rec_lead="I2", comparison=comparison)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.recommendation_mismatch" in codes


# ---------------------------------------------------------------------------
# External status agreement
# ---------------------------------------------------------------------------


def test_limited_research_strong_verification() -> None:
    body = _valid_body(state="research-limited", ext_status="limited", ext_rows="")
    # Inject a strong verification claim
    body = body.replace("- Confidence: moderate", "- Confidence: directly verified")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.limited_strong_verification" in codes


# ---------------------------------------------------------------------------
# Prohibited content
# ---------------------------------------------------------------------------


def test_prohibited_implementation_patch() -> None:
    body = _valid_body() + "\n```diff\n--- a/foo.py\n+++ b/foo.py\n@@ -1,1 +1,1 @@\n-old\n+new\n```\n"
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.prohibited_implementation" in codes
