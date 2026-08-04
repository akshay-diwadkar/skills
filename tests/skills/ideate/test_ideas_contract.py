from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[3] / "skills" / "research" / "ideate"
sys.path.insert(0, str(SKILL / "scripts"))

from ideas_contract import validate_ideas  # noqa: E402

# ---------------------------------------------------------------------------
# Candidate factory
# ---------------------------------------------------------------------------

CATEGORIES = ("caching", "compression", "pooling", "dedup", "batching", "sharding", "pipelining")


def _candidate(
    cid: str,
    category: str,
    support: tuple[str, str | None] = ("evidence-backed", "E1"),
    criteria_fit: str = "fits the criteria",
) -> str:
    label, qualifier = support
    if label == "evidence-backed":
        basis = f"evidence-backed: {qualifier or 'E1'}"
    elif label == "assumption-backed":
        basis = f"assumption-backed: {qualifier or 'users behave as assumed'}"
    else:
        basis = "hypothesis"
    return (
        f"### {cid}. Idea {cid}\n"
        "- Mechanism: mechanism\n"
        f"- Mechanism category: {category}\n"
        "- Why it applies: because\n"
        "- Evidence: narrative prose\n"
        f"- Support basis: {basis}\n"
        f"- Decision-criteria fit: {criteria_fit}\n"
        "- Expected impact: medium\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: low\n"
        "- Risk: low\n"
        "- Confidence: moderate\n"
        "- What would disconfirm it: failure\n"
        "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c\n\n"
    )


def _candidates(count: int = 3, support: tuple[str, str | None] = ("evidence-backed", "E1")) -> str:
    return "".join(_candidate(f"I{i + 1}", CATEGORIES[i], support) for i in range(count))


# ---------------------------------------------------------------------------
# Minimal valid body for reuse
# ---------------------------------------------------------------------------


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
    section6: str | None = None,
    stop_reason: str = "condition met",
) -> str:
    if candidates is None:
        candidates = _candidates(3)
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
    contextual_section = ""
    if contextual_rows:
        contextual_section = (
            "### Contextual evidence\n\n"
            "| ID | Claim | Origin | Verification |\n"
            "| --- | --- | --- | --- |\n"
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
    if section6 is None:
        section6 = (
            "- Strongest challenge to rank 1: challenge\n"
            "- Baseline / status quo comparison: better than baseline\n"
            "- Condition for a different winner: rank 2 wins if effort dominates\n"
            "- Remaining contradiction or uncertainty: none remaining \u2014 both validated on the same dataset\n"
        )
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
        f"- Research stop condition: stop after 5 sources or 30 minutes\n"
        f"- Research stop reason: {stop_reason}\n\n"
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
        + f"- Provisional lead: {actual_rec_lead} \u2014 Idea {lead}\n"
        + "- Why it leads: best ratio\n"
        + "- Why it beats rank 2: lower effort\n"
        + "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c\n"
        + "- What could change the ranking: new evidence\n"
        + "- Conditions that would change the ranking: hit rate < 20%\n"
        + "- How decision criteria were applied: latency dominated, then effort broke the tie\n\n"
        + "## 6. Contradictions and open questions\n"
        + section6
    )


# ---------------------------------------------------------------------------
# Valid cases
# ---------------------------------------------------------------------------


def test_valid_external_only() -> None:
    assert validate_ideas(_valid_body()) == []


def test_valid_hypothesis_experiment_first() -> None:
    body = _valid_body(
        state="experiment-first",
        ext_status="unavailable",
        ext_rows="",
        candidates=_candidates(3, support=("hypothesis", None)),
    )
    assert validate_ideas(body) == []


def test_valid_assumption_backed_decision_ready() -> None:
    body = _valid_body(
        ext_status="local-only",
        ext_rows="",
        candidates=_candidates(3, support=("assumption-backed", "users behave as assumed")),
    )
    assert validate_ideas(body) == []


def test_valid_research_limited() -> None:
    body = _valid_body(state="research-limited", ext_status="limited")
    assert validate_ideas(body) == []


def test_valid_stop_reason_with_explanation() -> None:
    body = _valid_body(stop_reason="diminishing returns \u2014 no new sources after the fifth")
    assert validate_ideas(body) == []


def test_valid_with_local_evidence(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    body = _valid_body(
        local_rows="| L1 | owns latency | src/app.py | line 1: # app | inspected |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_valid_with_contextual_evidence() -> None:
    body = _valid_body(
        ext_status="local-only",
        ext_rows="",
        contextual_rows="| C1 | user observed 500ms peaks | user-provided | user-stated |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1")),
    )
    assert validate_ideas(body) == []


def test_valid_contextual_plus_external() -> None:
    body = _valid_body(
        contextual_rows="| C1 | user observed 500ms peaks | direct observation | observed |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, C1")),
    )
    assert validate_ideas(body) == []


def test_all_external_statuses() -> None:
    for status in ("completed", "limited", "unavailable", "user-disabled", "local-only"):
        ext_rows = "| E1 | Found X | https://example.com | \u00a7 2 | 2026-07 | high |\n" if status != "local-only" else ""
        support = ("assumption-backed", "users behave as assumed") if status == "local-only" else ("evidence-backed", "E1")
        body = _valid_body(ext_status=status, ext_rows=ext_rows, candidates=_candidates(3, support=support))
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
    body = _valid_body().replace("### I1. Idea I1", "### I1.   ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_name" in codes


def test_empty_candidate_field() -> None:
    body = _valid_body().replace("- Mechanism: mechanism", "- Mechanism: ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_field" in codes


def test_empty_recommendation_field() -> None:
    body = _valid_body().replace("- Why it beats rank 2: lower effort", "- Why it beats rank 2: ")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_recommendation_field" in codes


# ---------------------------------------------------------------------------
# Support basis
# ---------------------------------------------------------------------------


def test_missing_support_basis_field() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1\n", "")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_field" in codes


def test_invalid_support_basis_syntax() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1\n", "- Support basis: intuition\n")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_support_basis" in codes


def test_evidence_backed_without_refs() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1\n", "- Support basis: evidence-backed:\n")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.evidence_backed_without_refs" in codes


def test_evidence_backed_unknown_ref() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1\n", "- Support basis: evidence-backed: E9\n")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.unknown_evidence_reference" in codes


def test_assumption_backed_without_qualifier() -> None:
    body = _valid_body().replace("- Support basis: evidence-backed: E1\n", "- Support basis: assumption-backed:\n")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_support_basis" in codes


def test_hypothesis_with_qualifier() -> None:
    body = _valid_body(
        candidates=(
            _candidate("I1", "caching", ("evidence-backed", "E1"))
            + _candidate("I2", "compression", ("hypothesis", None))
            + _candidate("I3", "pooling", ("evidence-backed", "E1"))
        )
    ).replace("- Support basis: hypothesis\n", "- Support basis: hypothesis: test it\n")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_support_basis" in codes


def test_evidence_ids_in_prose_not_parsed() -> None:
    body = _valid_body().replace(
        "- Why it applies: because",
        "- Why it applies: related to E9 mention in prose",
    )
    assert validate_ideas(body) == []


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


def test_misplaced_contextual_declaration() -> None:
    body = _valid_body() + "\n| C99 | Fake | user-provided | ver |\n"
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.misplaced_evidence_declaration" in codes


def test_evidence_table_wrong_header() -> None:
    body = _valid_body().replace("| Date/freshness | Relevance |", "| Date | Relevance |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_external_table_header" in codes


def test_evidence_table_wrong_row_width() -> None:
    body = _valid_body().replace("| E1 | Found X | https://example.com | § 2 | 2026-07 | high |", "| E1 | Found X | https://example.com | § 2 | high |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_external_table_row_width" in codes


def test_contextual_table_wrong_header() -> None:
    body = _valid_body(
        contextual_rows="| C1 | claim | user-provided | ver |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1")),
    ).replace("| ID | Claim | Origin | Verification |", "| ID | Claim | Origin |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_contextual_table_header" in codes


def test_contextual_table_wrong_row_width() -> None:
    body = _valid_body(
        contextual_rows="| C1 | claim | user-provided | ver |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1")),
    ).replace("| C1 | claim | user-provided | ver |", "| C1 | claim | user-provided |")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_contextual_table_row_width" in codes


def test_contextual_invalid_origin() -> None:
    body = _valid_body(
        contextual_rows="| C1 | claim | from my gut | ver |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1")),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_contextual_origin" in codes


def test_contextual_empty_verification() -> None:
    body = _valid_body(
        contextual_rows="| C1 | claim | user-provided | - |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1")),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_contextual_verification" in codes


def test_contextual_noncontiguous_ids() -> None:
    body = _valid_body(
        contextual_rows="| C1 | claim | user-provided | ver |\n| C3 | claim | observation | ver |\n",
        candidates=_candidates(3, support=("evidence-backed", "C1, C3")),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncontiguous_contextual_evidence" in codes


# ---------------------------------------------------------------------------
# Path & Hash Verification
# ---------------------------------------------------------------------------


def test_local_path_nonexistent(tmp_path: Path) -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/nonexistent.py | line 1 | inspected |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
    )
    codes = [e.code for e in validate_ideas(body, repo_root=tmp_path)]
    assert "ideas.local_path_not_found" in codes


def test_hash_verified_without_digest() -> None:
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1 | hash-verified |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.hash_verified_without_digest" in codes


def test_hash_verified_with_digest(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    digest = hashlib.sha256((tmp_path / "src" / "app.py").read_bytes()).hexdigest()
    body = _valid_body(
        local_rows=f"| L1 | claim | src/app.py | line 1 | hash-verified (sha256: {digest}) |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_hash_verified_digest_mismatch(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    body = _valid_body(
        local_rows="| L1 | claim | src/app.py | line 1 | hash-verified (sha256: " + ("a" * 64) + ") |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
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


def test_decision_ready_all_hypothesis_invalid() -> None:
    body = _valid_body(
        state="decision-ready",
        candidates=_candidates(3, support=("hypothesis", None)),
    )
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.unsupported_decision_ready" in codes


def test_decision_ready_mixed_hypothesis_valid() -> None:
    mixed = (
        _candidate("I1", "caching", ("evidence-backed", "E1"))
        + _candidate("I2", "compression", ("hypothesis", None))
        + _candidate("I3", "pooling", ("hypothesis", None))
    )
    body = _valid_body(state="decision-ready", candidates=mixed)
    assert validate_ideas(body) == []


def test_research_limited_with_completed_external() -> None:
    body = _valid_body(state="research-limited", ext_status="completed")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.incoherent_state_status" in codes


def test_research_limited_with_valid_local_verification(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app\n", encoding="utf-8")
    body = _valid_body(
        state="research-limited",
        ext_status="limited",
        local_rows="| L1 | verified local fact | src/app.py | line 1 | verified |\n",
        candidates=_candidates(3, support=("evidence-backed", "E1, L1")),
    )
    assert validate_ideas(body, repo_root=tmp_path) == []


def test_decisive_experiment_incomplete_in_candidate() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c",
        "- Cheapest decisive experiment: trial",
        1,
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_decisive_experiment_incomplete_in_recommendation() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c",
        "- Cheapest decisive experiment: trial",
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_empty_section6() -> None:
    body = _valid_body(
        section6=(
            "- Strongest challenge to rank 1: challenge\n"
            "- Baseline / status quo comparison: better than baseline\n"
            "- Condition for a different winner: rank 2 wins if effort dominates\n"
            "- Remaining contradiction or uncertainty: none remaining \u2014 both validated on the same dataset\n"
        )
    ).replace(
        "- Strongest challenge to rank 1: challenge\n"
        "- Baseline / status quo comparison: better than baseline\n"
        "- Condition for a different winner: rank 2 wins if effort dominates\n"
        "- Remaining contradiction or uncertainty: none remaining \u2014 both validated on the same dataset\n",
        "",
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.empty_section6" for d in diagnostics)


def test_section6_none_identified_insufficient() -> None:
    body = _valid_body(section6="- None identified.\n")
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.empty_section6_field" for d in diagnostics)


def test_section6_missing_challenge_field() -> None:
    body = _valid_body().replace("- Strongest challenge to rank 1: challenge\n", "")
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.empty_section6_field" for d in diagnostics)


# ---------------------------------------------------------------------------
# Criteria application
# ---------------------------------------------------------------------------


def test_missing_candidate_criteria_fit() -> None:
    body = _valid_body().replace("- Decision-criteria fit: fits the criteria\n", "")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.empty_candidate_field" in codes


def test_missing_recommendation_criteria_application() -> None:
    body = _valid_body().replace("- How decision criteria were applied: latency dominated, then effort broke the tie\n", "")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.missing_recommendation_field" in codes


# ---------------------------------------------------------------------------
# Research stop fields
# ---------------------------------------------------------------------------


def test_missing_research_stop_condition() -> None:
    body = _valid_body().replace("- Research stop condition: stop after 5 sources or 30 minutes\n", "")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.handoff_field_empty" in codes


def test_invalid_research_stop_reason() -> None:
    body = _valid_body(stop_reason="felt like it")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.invalid_research_stop_reason" in codes


# ---------------------------------------------------------------------------
# Exact recommendation lead matching
# ---------------------------------------------------------------------------


def test_lead_matches_rank1_exactly() -> None:
    assert validate_ideas(_valid_body()) == []


def test_lead_i10_does_not_match_rank1_i1() -> None:
    body = _valid_body().replace("- Provisional lead: I1 \u2014 Idea I1", "- Provisional lead: I10 \u2014 Idea I1")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.recommendation_mismatch" in codes


def test_lead_wrong_id_mismatch() -> None:
    body = _valid_body().replace("- Provisional lead: I1 \u2014 Idea I1", "- Provisional lead: I2 \u2014 Idea I2")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.recommendation_mismatch" in codes


def test_lead_rank1_i7_matches() -> None:
    candidates = _candidates(3) + _candidate("I4", "dedup", ("evidence-backed", "E1")) + _candidate("I5", "batching", ("evidence-backed", "E1")) + _candidate("I6", "sharding", ("evidence-backed", "E1")) + _candidate("I7", "pipelining", ("evidence-backed", "E1"))
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I7 | high | low | low | moderate | strong |\n"
        "| 2 | I1 | medium | medium | medium | low | moderate |\n"
        "| 3 | I2 | low | high | high | low | weak |\n"
        "| 4 | I3 | low | high | high | low | weak |\n"
        "| 5 | I4 | low | high | high | low | weak |\n"
        "| 6 | I5 | low | high | high | low | weak |\n"
        "| 7 | I6 | low | high | high | low | weak |\n"
    )
    body = _valid_body(candidates=candidates, comparison=comparison, lead="I7", rec_lead="I7")
    assert validate_ideas(body) == []


# ---------------------------------------------------------------------------
# Candidate heading grammar (canonical '### I1..I7. <name>')
# ---------------------------------------------------------------------------


def test_noncanonical_candidate_heading_out_of_range() -> None:
    body = _valid_body().replace("## 4. Comparison", "### I8. Extra\n\n## 4. Comparison")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


def test_noncanonical_candidate_heading_no_space() -> None:
    body = _valid_body().replace("### I1. Idea I1", "### I1.Idea I1")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


def test_noncanonical_candidate_heading_tab() -> None:
    body = _valid_body().replace("### I1. Idea I1", "###\tI1. Idea I1")
    codes = [e.code for e in validate_ideas(body)]
    assert "ideas.noncanonical_candidate_heading" in codes


# ---------------------------------------------------------------------------
# Comparison table row width (all ranks)
# ---------------------------------------------------------------------------


def test_comparison_row_width_rank4() -> None:
    candidates = _candidates(4)
    comparison = (
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | medium | low | moderate |\n"
        "| 3 | I3 | low | high | high | low | weak |\n"
        "| 4 | I4 | high | low |\n"
    )
    codes = [e.code for e in validate_ideas(_valid_body(candidates=candidates, comparison=comparison))]
    assert "ideas.invalid_comparison_table_row_width" in codes


# ---------------------------------------------------------------------------
# Decisive experiment components must have non-empty values
# ---------------------------------------------------------------------------


def test_decisive_experiment_empty_components_in_candidate() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c",
        "- Cheapest decisive experiment: metric: ; pass/fail: ; duration: ; cost:",
        1,
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


def test_decisive_experiment_empty_components_in_recommendation() -> None:
    body = _valid_body().replace(
        "- Cheapest decisive experiment: trial; metric: m; pass/fail: p; duration: d; cost/effort: c",
        "- Cheapest decisive experiment: metric: ; pass/fail: ; duration: ; cost:",
    )
    diagnostics = validate_ideas(body)
    assert any(d.code == "ideas.decisive_experiment_incomplete" for d in diagnostics)


# ---------------------------------------------------------------------------
# Template-derived valid artifact (drift guard)
# ---------------------------------------------------------------------------

TEMPLATE = (SKILL / "templates" / "ideas.md").read_text(encoding="utf-8")

SPECIAL_TOKEN_VALUES = {
    "origin": "user-provided",
}

LINE_AWARE_REPLACEMENTS = (
    ("- State: decision-ready | experiment-first | research-limited", "- State: decision-ready"),
    (
        "External research status: completed | limited | unavailable | user-disabled | local-only",
        "External research status: completed",
    ),
    (
        "- Research stop reason: condition met | diminishing returns | unavailable sources | user limit \u2014 <explanation>",
        "- Research stop reason: condition met",
    ),
    (
        "- Support basis: evidence-backed: <evidence IDs for I1> | assumption-backed: <material assumption> | hypothesis",
        "- Support basis: evidence-backed: E1, L1, C1",
    ),
    (
        "- Support basis: evidence-backed: <evidence IDs for I2> | assumption-backed: <material assumption> | hypothesis",
        "- Support basis: evidence-backed: E1",
    ),
    (
        "- Support basis: evidence-backed: <evidence IDs for I3> | assumption-backed: <material assumption> | hypothesis",
        "- Support basis: hypothesis",
    ),
)


def _fill_template(template: str) -> str:
    text = template
    for original, replacement in LINE_AWARE_REPLACEMENTS:
        assert original in text, f"template line not found: {original!r}"
        text = text.replace(original, replacement)

    def _substitute(match: re.Match[str]) -> str:
        token = match.group(1)
        return SPECIAL_TOKEN_VALUES.get(token, token)

    return re.sub(r"<([^>]+)>", _substitute, text)


def test_template_derived_artifact_is_valid() -> None:
    filled = _fill_template(TEMPLATE)
    assert validate_ideas(filled) == []
