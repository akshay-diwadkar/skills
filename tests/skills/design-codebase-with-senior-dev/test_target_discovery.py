import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def _setup_repo(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir(exist_ok=True)
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")


def test_autonomous_mode_requires_selected_candidate(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("status: selected", "status: deferred")
    diags = validate(text, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.selected_count_invalid" for d in diags)


def test_autonomous_mode_blocks_low_confidence(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("confidence: high", "confidence: low")
    diags = validate(text, "L1", tmp_path)
    assert any(d.code in {"discovery.candidate.confidence_invalid", "discovery.autonomous.low_confidence"} for d in diags)


def test_autonomous_mode_blocks_product_intent_required(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("product-intent-required: false", "product-intent-required: true")
    diags = validate(text, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.product_intent_required" for d in diags)


def test_discovery_only_mode_prohibits_selected_target(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    text = valid_v2_assessment("L0", mode="discovery-only").replace("status: deferred", "status: selected")
    diags = validate(text, "L0", tmp_path)
    assert any(d.code == "discovery.only.selected_prohibited" for d in diags)


def test_discovery_only_mode_requires_codebase_issue_auditor_handoff(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    text = valid_v2_assessment("L0", mode="discovery-only").replace("next: codebase-issue-auditor", "next: plan-with-senior-dev")
    diags = validate(text, "L0", tmp_path)
    assert any(d.code == "discovery.only.handoff_invalid" for d in diags)


def test_autonomous_exact_tie_one_selected(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")
    orig_t1 = "- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    t2_tied = orig_t1 + "\n- T-2: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 2 | status: deferred | reason: Target 2. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    tied_text = scaffold.replace(orig_t1, t2_tied)
    diags = validate(tied_text, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.ranking_tied" for d in diags)


def test_autonomous_exact_tie_zero_selected(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")
    orig_t1 = "- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    t1_deferred = orig_t1.replace("status: selected", "status: deferred")
    t2_tied = t1_deferred + "\n- T-2: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 2 | status: deferred | reason: Target 2. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    tied_text = scaffold.replace(orig_t1, t2_tied)
    diags = validate(tied_text, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.ranking_tied" for d in diags)


def test_autonomous_near_tie_within_threshold(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")
    orig_t1 = "- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    # Score diff 0.0 <= 2.0
    t2_near = orig_t1 + "\n- T-2: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 2 | status: deferred | reason: Target 2. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    tied_text = scaffold.replace(orig_t1, t2_near)
    diags = validate(tied_text, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.ranking_tied" for d in diags)


def test_autonomous_winner_outside_threshold(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")
    orig_t1 = "- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"
    # Score diff > 2.0
    t2_far = orig_t1 + "\n- T-2: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 2 | status: deferred | reason: Target 2. | correctness-risk: high | operational-risk: high | debt-interest: none | change-propagation: wide | state-ambiguity: high | scope-boundedness: low | reversibility: low | structural-confidence: low"
    text = scaffold.replace(orig_t1, t2_far)
    diags = validate(text, "L1", tmp_path)
    errs = [d for d in diags if not d.is_warning]
    assert errs == []


def test_autonomous_malformed_and_invalid_ranks(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")
    orig_t1 = "- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate. | correctness-risk: low | operational-risk: low | debt-interest: high | change-propagation: local | state-ambiguity: low | scope-boundedness: high | reversibility: high | structural-confidence: high"

    # Rank zero
    zero_rank = scaffold.replace("rank: 1", "rank: 0")
    diags0 = validate(zero_rank, "L1", tmp_path)
    assert any(d.code == "discovery.candidate.rank_invalid" for d in diags0)

    # Rank negative / malformed
    neg_rank = scaffold.replace("rank: 1", "rank: -2")
    diags_neg = validate(neg_rank, "L1", tmp_path)
    assert any(d.code in {"discovery.candidate.rank_malformed", "discovery.candidate.rank_invalid"} for d in diags_neg)

    # Duplicate ranks
    t2_dup = orig_t1 + "\n- T-2: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: deferred | reason: Target 2. | correctness-risk: high | operational-risk: high | debt-interest: none | change-propagation: wide | state-ambiguity: high | scope-boundedness: low | reversibility: low | structural-confidence: low"
    dup_rank = scaffold.replace(orig_t1, t2_dup)
    diags_dup = validate(dup_rank, "L1", tmp_path)
    assert any(d.code == "discovery.candidate.rank_duplicate" for d in diags_dup)


def test_autonomous_low_boundedness_and_reversibility(tmp_path: Path) -> None:
    _setup_repo(tmp_path)
    scaffold = valid_v2_assessment("L1", mode="autonomous-discovery")

    low_bound = scaffold.replace("scope-boundedness: high", "scope-boundedness: low")
    diags_b = validate(low_bound, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.unbounded" for d in diags_b)

    low_rev = scaffold.replace("reversibility: high", "reversibility: low")
    diags_r = validate(low_rev, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.low_reversibility" for d in diags_r)

    low_struct = scaffold.replace("structural-confidence: high", "structural-confidence: low")
    diags_s = validate(low_struct, "L1", tmp_path)
    assert any(d.code == "discovery.autonomous.low_confidence" for d in diags_s)
