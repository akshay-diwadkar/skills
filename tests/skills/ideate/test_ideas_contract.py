from __future__ import annotations

import hashlib
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "research" / "ideate"
sys.path.insert(0, str(SKILL / "scripts"))

from ideas_contract import validate_ideas  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal valid bodies for reuse
# ---------------------------------------------------------------------------


def _section6() -> str:
    return (
        "## 6. Contradictions and open questions\n"
        "- Strongest challenge to rank 1: rank 2 may win if effort dominates\n"
        "- Baseline comparison: baseline p99 remains 500ms without change\n"
        "- Alternate winner condition: I2 wins if compression yields >40% reduction\n"
        "- Remaining uncertainty: none remaining — E1 benchmark covers primary risk\n"
    )


def _candidate_block(
    cid: str,
    name: str,
    mechanism: str,
    category: str,
    why: str,
    support: str,
    criteria_fit: str = "best latency-effort trade-off",
) -> str:
    return (
        f"### {cid}. {name}\n"
        f"- Mechanism: {mechanism}\n"
        f"- Mechanism category: {category}\n"
        f"- Why it applies: {why}\n"
        f"- Support basis: {support}\n"
        f"- Decision-criteria fit: {criteria_fit}\n"
        "- Expected impact: high\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: low\n"
        "- Risk: low\n"
        "- Confidence: moderate\n"
        "- What would disconfirm it: Z fails\n"
        "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n\n"
    )


def _valid_body(
    state: str = "decision-ready",
    ext_status: str = "completed",
    local_rows: str = "",
    contextual_rows: str = "",
    ext_rows: str = "| E1 | Found X | https://example.com | \u00a7 2 | 2026-07 | high |\n",
    candidates: str | None = None,
    comparison: str | None = None,
    lead: str = "I1",
    rec_lead: str | None = None,
) -> str:
    has_ext = bool(ext_rows)
    if candidates is None:
        ev_support = "evidence-backed: E1" if has_ext else "evidence-backed: L1"
        candidates = (
            _candidate_block("I1", "Alpha", "do X", "caching", "because Y", ev_support)
            + _candidate_block("I2", "Beta", "do Y", "compression", "because Z", ev_support, "moderate latency gain")
            + _candidate_block("I3", "Gamma", "do Z", "pooling", "because W", ev_support, "limited criteria fit")
        )
    if comparison is None:
        comparison = (
            "| Rank | Candidate | Impact | Effort | Risk | Confidence | Support strength |\n"
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
    contextual_section = ""
    if contextual_rows:
        contextual_section = (
            "### Contextual evidence\n\n"
            "| ID | Claim | Source description | Locator | Verification |\n"
            "| --- | --- | --- | --- | --- |\n"
            + contextual_rows
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
        f"- Research limitations: none\n"
        f"- Research stop condition: sufficient benchmark evidence gathered\n"
        f"- Research stop reason: condition met — E1 answers primary question\n\n"
        f"## 2. Evidence\n\n"
        + local_section
        + contextual_section
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
        + "- How decision criteria were applied: rank 1 minimizes latency with lowest effort\n"
        + "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n"
        + "- What could change the ranking: new evidence\n"
        + "- Conditions that would change the ranking: hit rate < 20%\n\n"
        + _section6()
    )


def _local_candidates() -> str:
    """Three candidates citing both local and external evidence (E1, L1)."""
    return (
        _candidate_block("I1", "Alpha", "do X", "cat1", "Y", "evidence-backed: E1, L1")
        + _candidate_block("I2", "Beta", "do Y", "cat2", "Z", "evidence-backed: E1", "secondary fit")
        + _candidate_block("I3", "Gamma", "do Z", "cat3", "W", "evidence-backed: L1", "weakest fit")
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
            _local_candidates()
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
                _candidate_block("I1", "Alpha", "do X", "cat1", "Y", "evidence-backed: L1")
                + _candidate_block("I2", "Beta", "do Y", "cat2", "Z", "evidence-backed: L1", "secondary")
                + _candidate_block("I3", "Gamma", "do Z", "cat3", "W", "evidence-backed: L1", "tertiary")
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


def test_candidate_support_from_support_basis_field_only() -> None:
    # Candidate text contains E9 in description but Support basis cites E1 — should NOT error on E9
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
        candidates=_local_candidates(),
    )
    codes = [e.code for e in validate_ideas(body, repo_root=tmp_path)]
    assert "ideas.local_path_not_found" in codes


def test_hash_verified_without_digest() -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1 | hash-verified |\n",
        candidates=_local_candidates(),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.hash_verified_without_digest" in codes


def test_hash_verified_with_digest(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    digest = hashlib.sha256((tmp_path / "src" / "app.py").read_bytes()).hexdigest()
    body = _valid_body(
        local_rows=f"| L1 | claim | src/app.py | line 1 | hash-verified (sha256: {digest}) |\n",
        candidates=_local_candidates(),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_hash_verified_digest_mismatch(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1 | hash-verified (sha256: " + ("a" * 64) + ") |\n",
        candidates=_local_candidates(),
    )
    codes = [e.code for e in validate_ideas(body, repo_root=tmp_path)]
    assert "ideas.hash_verified_digest_mismatch" in codes


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
        candidates=_local_candidates(),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_decisive_experiment_incomplete_in_candidate() -> None:
    incomplete_i1 = _candidate_block("I1", "Alpha", "do X", "cat1", "Y", "evidence-backed: E1").replace(
        "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low",
        "- Cheapest decisive experiment: try Z",
    )
    body = _valid_body(
        candidates=(
            incomplete_i1
            + _candidate_block("I2", "Beta", "do Y", "cat2", "Z", "evidence-backed: E1", "secondary")
            + _candidate_block("I3", "Gamma", "do Z", "cat3", "W", "evidence-backed: E1", "tertiary")
        ),
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_decisive_experiment_incomplete_in_recommendation() -> None:
    body = _valid_body()
    # Replace recommendation experiment with incomplete string
    body = body.replace(
        "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low",
        "- Cheapest decisive experiment: try Z",
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_empty_section6() -> None:
    body = _valid_body()
    body = body.replace(_section6(), "## 6. Contradictions and open questions\n\n")
    diagnostics = validate_ideas(body)
    codes = [d.code for d in diagnostics]
    assert "ideas.empty_section6" in codes
    assert "ideas.missing_adversarial_field" not in codes


# ---------------------------------------------------------------------------
# Candidate heading grammar (canonical '### I1..I7. <name>')
# ---------------------------------------------------------------------------


def test_noncanonical_candidate_heading_out_of_range() -> None:
    body = _valid_body().replace("## 4. Comparison", "### I8. Extra\n\n## 4. Comparison")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


def test_noncanonical_candidate_heading_no_space() -> None:
    body = _valid_body().replace("### I1. Alpha", "### I1.Alpha")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


def test_noncanonical_candidate_heading_tab() -> None:
    body = _valid_body().replace("### I1. Alpha", "###\tI1. Alpha")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


# ---------------------------------------------------------------------------
# Comparison table row width (all ranks)
# ---------------------------------------------------------------------------


def test_comparison_row_width_rank4() -> None:
    cands = (
        _candidate_block("I1", "Alpha", "do X", "caching", "because Y", "evidence-backed: E1")
        + _candidate_block("I2", "Beta", "do Y", "compression", "because Z", "evidence-backed: E1", "secondary")
        + _candidate_block("I3", "Gamma", "do Z", "pooling", "because W", "evidence-backed: E1", "tertiary")
        + _candidate_block("I4", "Delta", "do W", "dedup", "because V", "evidence-backed: E1", "quaternary")
    )
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Support strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | medium | low | moderate |\n"
        "| 3 | I3 | low | high | high | low | weak |\n"
        "| 4 | I4 | high | low |\n"
    )
    codes = [e.code for e in validate_ideas(_valid_body(candidates=cands, comparison=comparison))]
    assert "ideas.invalid_comparison_table_row_width" in codes


# ---------------------------------------------------------------------------
# Decisive experiment components must have non-empty values
# ---------------------------------------------------------------------------


def test_decisive_experiment_empty_components_in_candidate() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low",
        "- Cheapest decisive experiment: metric: ; pass/fail: ; duration: ; cost:",
        1,
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_decisive_experiment_empty_components_in_recommendation() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low",
        "- Cheapest decisive experiment: metric: ; pass/fail: ; duration: ; cost:",
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


# ---------------------------------------------------------------------------
# Contract v2: support basis, criteria, adversarial, research stop, lead ID
# ---------------------------------------------------------------------------


def test_invalid_support_basis_prefix() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1", "- Support basis: intuition")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_support_basis" in codes


def test_unknown_support_reference() -> None:
    body = _valid_body().replace("evidence-backed: E1", "evidence-backed: C9", 1)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.unknown_support_reference" in codes


def test_decision_ready_hypothesis_lead() -> None:
    body = _valid_body(
        candidates=(
            _candidate_block("I1", "Alpha", "do X", "caching", "Y", "hypothesis: untested cache benefit")
            + _candidate_block("I2", "Beta", "do Y", "compression", "Z", "evidence-backed: E1", "secondary")
            + _candidate_block("I3", "Gamma", "do Z", "pooling", "W", "evidence-backed: E1", "tertiary")
        )
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.decision_ready_hypothesis_lead" in codes


def test_experiment_first_allows_hypothesis_lead() -> None:
    body = _valid_body(
        state="experiment-first",
        candidates=(
            _candidate_block("I1", "Alpha", "do X", "caching", "Y", "hypothesis: untested cache benefit")
            + _candidate_block("I2", "Beta", "do Y", "compression", "Z", "evidence-backed: E1", "secondary")
            + _candidate_block("I3", "Gamma", "do Z", "pooling", "W", "evidence-backed: E1", "tertiary")
        ),
    )
    assert validate_ideas(body) == []


def test_missing_adversarial_field() -> None:
    body = _valid_body().replace(
        "- Strongest challenge to rank 1: rank 2 may win if effort dominates",
        "- Strongest challenge to rank 1: ",
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_adversarial_field" in codes


def test_missing_criteria_fit() -> None:
    body = _valid_body().replace("- Decision-criteria fit: best latency-effort trade-off", "- Decision-criteria fit: ", 1)
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_criteria_fit" in codes


def test_missing_criteria_application() -> None:
    body = _valid_body().replace(
        "- How decision criteria were applied: rank 1 minimizes latency with lowest effort",
        "- How decision criteria were applied: ",
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_criteria_application" in codes


def test_invalid_research_stop_reason() -> None:
    body = _valid_body().replace(
        "- Research stop reason: condition met — E1 answers primary question",
        "- Research stop reason: finished researching",
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_research_stop_reason" in codes


def test_research_stop_reason_rejects_false_prefix() -> None:
    for bad in ("user limited access", "condition meticulous scan"):
        body = _valid_body().replace(
            "- Research stop reason: condition met — E1 answers primary question",
            f"- Research stop reason: {bad}",
        )
        codes = [e.code for e in validate_ideas(body)]
        assert "ideas.invalid_research_stop_reason" in codes, bad


def test_research_stop_reason_accepts_exact_and_noted_forms() -> None:
    for ok in (
        "condition met",
        "condition met — E1 answers primary question",
        "diminishing returns - no new sources",
        "user limit",
    ):
        body = _valid_body().replace(
            "- Research stop reason: condition met — E1 answers primary question",
            f"- Research stop reason: {ok}",
        )
        assert validate_ideas(body) == [], ok


def test_recommendation_mismatch_exact_id() -> None:
    body = _valid_body(rec_lead="I10")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.recommendation_mismatch" in codes


def test_recommendation_mismatch_non_token_suffix() -> None:
    body = _valid_body(rec_lead="I1foo")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.recommendation_mismatch" in codes


def test_recommendation_match_exact_i1() -> None:
    body = _valid_body(rec_lead="I1")
    assert not any(d.code == "ideas.recommendation_mismatch" for d in validate_ideas(body))


def test_valid_contextual_evidence() -> None:
    body = _valid_body(
        ext_rows="",
        ext_status="local-only",
        contextual_rows="| C1 | user tried caching before | prior attempt | 2025 pilot | user-reported |\n",
        candidates=(
            _candidate_block("I1", "Alpha", "do X", "caching", "Y", "evidence-backed: C1")
            + _candidate_block("I2", "Beta", "do Y", "compression", "Z", "assumption-backed: CPU headroom exists", "secondary")
            + _candidate_block("I3", "Gamma", "do Z", "pooling", "W", "hypothesis: pooling helps bursts", "tertiary")
        ),
    )
    assert validate_ideas(body) == []


def test_missing_research_stop_fields() -> None:
    body = _valid_body().replace("- Research stop condition: sufficient benchmark evidence gathered\n", "")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.handoff_field_empty" in codes

