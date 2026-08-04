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
    has_ext = bool(ext_rows)
    if candidates is None:
        ev_ref = "E1" if has_ext else "L1"
        candidates = (
            "### I1. Alpha\n"
            f"- Mechanism: do X\n- Mechanism category: caching\n- Why it applies: because Y\n- Evidence: {ev_ref}\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
            "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n\n"
            "### I2. Beta\n"
            f"- Mechanism: do Y\n- Mechanism category: compression\n- Why it applies: because Z\n- Evidence: {ev_ref}\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A fails\n"
            "- Cheapest decisive experiment: try A; metric: size; pass/fail: >20%; duration: 1d; cost/effort: low\n\n"
            "### I3. Gamma\n"
            f"- Mechanism: do Z\n- Mechanism category: pooling\n- Why it applies: because W\n- Evidence: {ev_ref}\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B fails\n"
            "- Cheapest decisive experiment: try B; metric: time; pass/fail: <10ms; duration: 1d; cost/effort: medium\n\n"
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
    actual_rec_lead = rec_lead if rec_lead is not None else lead
    return (
        f"# Ideas: reduce latency\n\n"
        f"## 1. Handoff\n"
        f"- State: {state}\n"
        f"- Goal: reduce latency\n"
        f"- Success measure: p99 < 200ms\n"
        f"- Baseline / status quo: p99 = 500ms\n"
        f"- Scope: API layer\n"
        f"- Non-goals: database\n"
        f"- Assumptions: current p99 = 500 ms\n"
        f"- Material unknowns: none\n"
        f"- Decision horizon: Q3 2026\n"
        f"- Decision criteria: latency, effort\n"
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
        + "- Why it beats rank 2: lower effort\n"
        + "- Cheapest decisive experiment: try Z\n"
        + "- What could change the ranking: new evidence\n"
        + "- Conditions that would change the ranking: hit rate < 20%\n\n"
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
        local_rows="| L1 | owns latency | src/app.py | line 1: # app | inspected |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: because Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z fails\n"
            "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: because Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A fails\n"
            "- Cheapest decisive experiment: try A; metric: size; pass/fail: >20%; duration: 1d; cost/effort: low\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: because W\n- Evidence: L1\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B fails\n"
            "- Cheapest decisive experiment: try B; metric: time; pass/fail: <10ms; duration: 1d; cost/effort: medium\n\n"
        ),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_valid_local_only(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    local_rows = "| L1 | owns latency | src/app.py | line 1: # app | inspected |\n"
    body = _valid_body(state="decision-ready", ext_status="local-only", local_rows=local_rows, ext_rows="")
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_all_external_statuses() -> None:
    for status in ("completed", "limited", "unavailable", "user-disabled", "local-only"):
        ext_rows = "| E1 | Found X | https://example.com | \u00a7 2 | 2026-07 | high |\n" if status != "local-only" else ""
        local_rows = "| L1 | claim | src/app.py | line 1 | inspected |\n" if status == "local-only" else ""
        cands = None
        if status == "local-only":
            cands = (
                "### I1. Alpha\n"
                "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: Y\n- Evidence: L1\n"
                "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
                "- Confidence: moderate\n- What would disconfirm it: Z\n"
                "- Cheapest decisive experiment: try Z; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
                "### I2. Beta\n"
                "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: Z\n- Evidence: L1\n"
                "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
                "- Confidence: low\n- What would disconfirm it: A\n"
                "- Cheapest decisive experiment: try A; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
                "### I3. Gamma\n"
                "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: W\n- Evidence: L1\n"
                "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
                "- Confidence: low\n- What would disconfirm it: B\n"
                "- Cheapest decisive experiment: try B; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            )
        body = _valid_body(ext_status=status, ext_rows=ext_rows, local_rows=local_rows, candidates=cands)
        errors = validate_ideas(body)
        assert errors == [], f"status={status!r}: {errors}"


# ---------------------------------------------------------------------------
# Missing / reordered / duplicate headings & title
# ---------------------------------------------------------------------------


def test_missing_required_heading() -> None:
    body = _valid_body().replace("## 4. Comparison", "## 4. Broken")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_heading" in codes or "ideas.heading_order" in codes


def test_duplicate_heading() -> None:
    body = _valid_body().replace("## 1. Handoff", "## 1. Handoff\n## 1. Handoff")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.duplicate_heading" in codes


def test_empty_goal_title() -> None:
    body = _valid_body().replace("# Ideas: reduce latency", "# Ideas:   ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_title" in codes


def test_title_not_first_line() -> None:
    body = "\n\n" + _valid_body()
    assert validate_ideas(body) == []


# ---------------------------------------------------------------------------
# Required fields & Empty fields
# ---------------------------------------------------------------------------


def test_missing_handoff_fields() -> None:
    body = _valid_body().replace("- Success measure: p99 < 200ms", "- Success measure: ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.handoff_field_empty" in codes


def test_empty_candidate_name() -> None:
    body = _valid_body().replace("### I1. Alpha", "### I1.   ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_name" in codes


def test_empty_candidate_field() -> None:
    body = _valid_body().replace("- Mechanism: do X", "- Mechanism: ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_field" in codes


def test_empty_recommendation_field() -> None:
    body = _valid_body().replace("- Why it beats rank 2: lower effort", "- Why it beats rank 2: ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_recommendation_field" in codes


# ---------------------------------------------------------------------------
# Mechanism Category & Diversity
# ---------------------------------------------------------------------------


def test_duplicate_mechanism_category() -> None:
    body = _valid_body().replace("- Mechanism category: compression", "- Mechanism category: caching")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.duplicate_mechanism_category" in codes


# ---------------------------------------------------------------------------
# Evidence ID Scoping & Tables
# ---------------------------------------------------------------------------


def test_misplaced_evidence_declaration() -> None:
    body = _valid_body() + "\n| L99 | Fake | path | loc | ver |\n"
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.misplaced_evidence_declaration" in codes


def test_candidate_evidence_from_evidence_field_only() -> None:
    # Candidate text contains E9 in description but Evidence: field has E1 — should NOT error on E9
    body = _valid_body()
    body = body.replace("Why it applies: because Y", "Why it applies: related to E9 mention in docs")
    assert validate_ideas(body) == []


def test_evidence_table_wrong_header() -> None:
    body = _valid_body().replace("| Date/freshness | Relevance |", "| Date | Relevance |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_external_table_header" in codes


def test_evidence_table_wrong_row_width() -> None:
    body = _valid_body().replace("| E1 | Found X | https://example.com | § 2 | 2026-07 | high |", "| E1 | Found X | https://example.com | § 2 | high |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_external_table_row_width" in codes


# ---------------------------------------------------------------------------
# Path & Hash Verification
# ---------------------------------------------------------------------------


def test_local_path_nonexistent(tmp_path: Path) -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/nonexistent.py | line 1 | inspected |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
        ),
    )
    codes = [e.code for e in validate_ideas(body, repo_root=tmp_path)]
    assert "ideas.local_path_not_found" in codes


def test_hash_verified_without_digest() -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1 | hash-verified |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
        ),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.hash_verified_without_digest" in codes


def test_hash_verified_with_digest(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    digest = "a" * 64
    body = _valid_body(
        local_rows=f"| L1 | claim | src/app.py | line 1 | hash-verified (sha256: {digest}) |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
        ),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


# ---------------------------------------------------------------------------
# Section 7 Restrictions
# ---------------------------------------------------------------------------


def test_section7_routes_to_implement_plan() -> None:
    body = _valid_body() + "\n## 7. Optional downstream action\nRoute directly to implement-plan.\n"
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.prohibited_direct_implementation" in codes


def test_section7_before_section6() -> None:
    body = _valid_body()
    sec6 = "## 6. Contradictions and open questions"
    sec7 = "## 7. Optional downstream action\nUse design-codebase.\n\n"
    idx6 = body.find(sec6)
    reordered = body[:idx6] + sec7 + body[idx6:]
    codes = [e.code for e in validate_ideas(reordered)]
    assert "ideas.heading_order" in codes


# ---------------------------------------------------------------------------
# State & Status Coherence
# ---------------------------------------------------------------------------


def test_research_limited_with_completed_external() -> None:
    body = _valid_body(state="research-limited", ext_status="completed")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.incoherent_state_status" in codes


def test_research_limited_with_valid_local_verification(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    # Local evidence has verified claim, external status is limited
    body = _valid_body(
        state="research-limited",
        ext_status="limited",
        local_rows="| L1 | verified local fact | src/app.py | line 1 | verified |\n",
        candidates=(
            "### I1. Alpha\n"
            "- Mechanism: do X\n- Mechanism category: cat1\n- Why it applies: Y\n- Evidence: E1, L1\n"
            "- Expected impact: high\n- Assumptions and dependencies: none\n- Effort: low\n- Risk: low\n"
            "- Confidence: moderate\n- What would disconfirm it: Z\n"
            "- Cheapest decisive experiment: try Z; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I2. Beta\n"
            "- Mechanism: do Y\n- Mechanism category: cat2\n- Why it applies: Z\n- Evidence: E1\n"
            "- Expected impact: medium\n- Assumptions and dependencies: none\n- Effort: medium\n- Risk: medium\n"
            "- Confidence: low\n- What would disconfirm it: A\n"
            "- Cheapest decisive experiment: try A; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
            "### I3. Gamma\n"
            "- Mechanism: do Z\n- Mechanism category: cat3\n- Why it applies: W\n- Evidence: L1\n"
            "- Expected impact: low\n- Assumptions and dependencies: none\n- Effort: high\n- Risk: high\n"
            "- Confidence: low\n- What would disconfirm it: B\n"
            "- Cheapest decisive experiment: try B; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
        ),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []
