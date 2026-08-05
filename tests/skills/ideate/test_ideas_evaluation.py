from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
IDEATE_TEST_DIR = ROOT / "tests" / "skills" / "ideate"
EVAL_DIR = IDEATE_TEST_DIR / "evals"
SKILL = ROOT / "skills" / "research" / "ideate"
FIXTURES = EVAL_DIR / "fixtures"

sys.path.insert(0, str(IDEATE_TEST_DIR))
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(SKILL / "scripts"))

from ideas_contract import validate_ideas  # noqa: E402
from score_ideate_evaluation import score_ideas_draft  # type: ignore[import-not-found] # noqa: E402


def test_eval_harness_scoring_valid_draft(tmp_path: Path) -> None:
    from test_ideas_contract import _valid_body  # type: ignore[import-not-found]

    draft = tmp_path / "ideas.md"
    draft.write_text(_valid_body(), encoding="utf-8")
    results = score_ideas_draft(draft)
    assert results["valid"] is True
    assert results["score_pct"] == 100.0
    assert results["passed_dimensions"] == 12


@pytest.mark.parametrize(
    "fixture_name",
    [
        "valid_full.md",
        "valid_engineering_repo.md",
        "valid_scientific_external.md",
        "valid_operations_contextual.md",
        "valid_creative_zero_repo.md",
    ],
)
def test_eval_harness_valid_domain_fixtures(fixture_name: str) -> None:
    results = score_ideas_draft(FIXTURES / fixture_name)
    assert results["valid"] is True
    assert results["score_pct"] == 100.0
    assert results["passed_dimensions"] == 12


@pytest.mark.parametrize(
    ("fixture_name", "expected_code"),
    [
        ("invalid_no_support_basis.md", "ideas.invalid_support_basis"),
        ("invalid_decision_ready_hypothesis_lead.md", "ideas.decision_ready_hypothesis_lead"),
        ("invalid_missing_adversarial.md", "ideas.missing_adversarial_field"),
        ("invalid_criteria_not_applied.md", "ideas.missing_criteria_application"),
        ("invalid_research_stop_missing.md", "ideas.handoff_field_empty"),
        ("invalid_lead_i10_confusion.md", "ideas.recommendation_mismatch"),
        ("invalid_unknown_contextual_ref.md", "ideas.unknown_support_reference"),
    ],
)
def test_eval_harness_invalid_fixtures(fixture_name: str, expected_code: str) -> None:
    results = score_ideas_draft(FIXTURES / fixture_name)
    assert results["valid"] is False
    assert any(expected_code in d for d in results["diagnostics"])


def test_eval_harness_scoring_missing_experiment_subfields_fixture() -> None:
    results = score_ideas_draft(FIXTURES / "missing_experiment_subfields.md")
    assert results["valid"] is False
    assert results["checks"]["8_experiment_decisiveness"] is False


def test_eval_harness_scoring_empty_section6_fixture() -> None:
    results = score_ideas_draft(FIXTURES / "empty_section6.md")
    assert results["valid"] is False
    assert results["checks"]["9_adversarial_structure"] is False
    assert any("ideas.empty_section6" in d for d in results["diagnostics"])
    assert not any("ideas.missing_adversarial_field" in d for d in results["diagnostics"])


def test_eval_harness_scoring_weak_fixture() -> None:
    results = score_ideas_draft(FIXTURES / "structurally_valid_weak.md")
    assert results["valid"] is False
    assert results["checks"]["5_lack_of_duplication"] is False
    assert results["score_pct"] < 100.0


def _filled_template_body() -> str:
    """Fill the live template with minimal valid v2 values to catch template drift."""
    text = (SKILL / "templates" / "ideas.md").read_text(encoding="utf-8")

    required_markers = (
        "- Support basis: evidence-backed: E1",
        "- Support basis: assumption-backed: <material assumption>",
        "- Support basis: hypothesis: <unverified claim>",
        "- Decision-criteria fit:",
        "- Research stop condition:",
        "- Research stop reason:",
        "- How decision criteria were applied:",
        "- Strongest challenge to rank 1:",
        "Support strength",
        "### Contextual evidence",
    )
    for marker in required_markers:
        if marker not in text:
            raise AssertionError(f"template drift: required marker missing: {marker!r}")

    text = text.replace("# Ideas: <goal>", "# Ideas: reduce latency", 1)
    text = text.replace(
        "- State: decision-ready | experiment-first | research-limited",
        "- State: experiment-first",
        1,
    )
    handoff_fills = {
        "- Goal:": "- Goal: reduce latency",
        "- Success measure:": "- Success measure: p99 < 200ms",
        "- Baseline / status quo:": "- Baseline / status quo: p99 = 500ms",
        "- Scope:": "- Scope: API layer",
        "- Non-goals:": "- Non-goals: database",
        "- Assumptions:": "- Assumptions: current p99 = 500 ms",
        "- Material unknowns:": "- Material unknowns: none",
        "- Decision horizon:": "- Decision horizon: Q3 2026",
        "- Decision criteria:": "- Decision criteria: latency, effort",
        "- Selected source playbooks:": "- Selected source playbooks: software/engineering",
        "- Research coverage:": "- Research coverage: docs, benchmarks",
        "- Research limitations:": "- Research limitations: none",
        "- Research stop condition:": "- Research stop condition: sufficient benchmark evidence gathered",
    }
    for old, new in handoff_fills.items():
        text = text.replace(old, new, 1)

    text = text.replace(
        (
            "- Research stop reason: condition met | diminishing returns | "
            "unavailable sources | user limit — <optional note>"
        ),
        "- Research stop reason: condition met — E1 answers primary question",
        1,
    )
    text = text.replace(
        "External research status: completed | limited | unavailable | user-disabled | local-only",
        "External research status: completed",
        1,
    )
    text = text.replace(
        "| ID | Finding | Source | Locator | Date/freshness | Relevance |\n"
        "| --- | --- | --- | --- | --- | --- |\n",
        "| ID | Finding | Source | Locator | Date/freshness | Relevance |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| E1 | Found X | https://example.com | § 2 | 2026-07 | high |\n",
        1,
    )
    text = re.sub(
        r"\n### Local evidence\n\n\| ID \| Claim \| Source path \| Locator \| Verification \|\n"
        r"\| --- \| --- \| --- \| --- \| --- \|\n",
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"\n### Contextual evidence\n\n\| ID \| Claim \| Source description \| Locator \| Verification \|\n"
        r"\| --- \| --- \| --- \| --- \| --- \|\n",
        "\n",
        text,
        count=1,
    )

    candidates = [
        (
            "### I1. <name>",
            "### I1. Alpha",
            "do X",
            "caching",
            "because Y",
            "evidence-backed: E1",
            "best latency-effort trade-off",
        ),
        (
            "### I2. <name>",
            "### I2. Beta",
            "do Y",
            "compression",
            "because Z",
            "assumption-backed: CPU headroom exists",
            "moderate latency gain",
        ),
        (
            "### I3. <name>",
            "### I3. Gamma",
            "do Z",
            "pooling",
            "because W",
            "hypothesis: pooling helps bursts",
            "limited criteria fit",
        ),
    ]
    for heading_old, heading_new, mechanism, category, why, support, fit in candidates:
        block_start = text.index(heading_old)
        next_heading = text.find("\n### ", block_start + 1)
        section_end = text.find("\n## 4. Comparison", block_start)
        block_end = next_heading if next_heading != -1 and (section_end == -1 or next_heading < section_end) else section_end
        if block_end == -1:
            raise AssertionError(f"template drift: could not locate end of {heading_old}")
        filled_block = (
            f"{heading_new}\n"
            f"- Mechanism: {mechanism}\n"
            f"- Mechanism category: {category}\n"
            f"- Why it applies: {why}\n"
            f"- Support basis: {support}\n"
            f"- Decision-criteria fit: {fit}\n"
            "- Expected impact: high\n"
            "- Assumptions and dependencies: none\n"
            "- Effort: low\n"
            "- Risk: low\n"
            "- Confidence: moderate\n"
            "- What would disconfirm it: Z fails\n"
            "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; "
            "duration: 1d; cost/effort: low\n"
        )
        text = text[:block_start] + filled_block + text[block_end:]

    text = text.replace("| 1 | I1 | ... | ... | ... | ... | ... |", "| 1 | I1 | high | low | low | moderate | strong |", 1)
    text = text.replace("| 2 | I2 | ... | ... | ... | ... | ... |", "| 2 | I2 | medium | medium | medium | low | moderate |", 1)
    text = text.replace("| 3 | I3 | ... | ... | ... | ... | ... |", "| 3 | I3 | low | high | high | low | weak |", 1)

    rec_fills = {
        "- Provisional lead: I1 — <name>": "- Provisional lead: I1 — Alpha",
        "- Why it leads:": "- Why it leads: best ratio",
        "- Why it beats rank 2:": "- Why it beats rank 2: lower effort",
        "- How decision criteria were applied:": (
            "- How decision criteria were applied: rank 1 minimizes latency with lowest effort"
        ),
        (
            "- Cheapest decisive experiment: <action>; metric: <metric>; pass/fail: <rule>; "
            "duration: <bound>; cost/effort: <bound>"
        ): (
            "- Cheapest decisive experiment: try Z; metric: hit rate; pass/fail: >50%; "
            "duration: 1d; cost/effort: low"
        ),
        "- What could change the ranking:": "- What could change the ranking: new evidence",
        "- Conditions that would change the ranking:": (
            "- Conditions that would change the ranking: hit rate < 20%"
        ),
        "- Strongest challenge to rank 1:": (
            "- Strongest challenge to rank 1: rank 2 may win if effort dominates"
        ),
        "- Baseline comparison:": "- Baseline comparison: baseline p99 remains 500ms without change",
        "- Alternate winner condition:": (
            "- Alternate winner condition: I2 wins if compression yields >40% reduction"
        ),
        "- Remaining uncertainty:": (
            "- Remaining uncertainty: none remaining — E1 benchmark covers primary risk"
        ),
    }
    for old, new in rec_fills.items():
        if old not in text:
            raise AssertionError(f"template drift: expected fragment missing: {old!r}")
        text = text.replace(old, new, 1)

    return text


def test_template_derived_artifact_validates(tmp_path: Path) -> None:
    body = _filled_template_body()
    assert validate_ideas(body) == []
    draft = tmp_path / "ideas.md"
    draft.write_text(body, encoding="utf-8")
    results = score_ideas_draft(draft)
    assert results["valid"] is True
    assert results["score_pct"] == 100.0
    golden = FIXTURES / "valid_from_template.md"
    assert golden.read_text(encoding="utf-8") == body, (
        "valid_from_template.md drifted from live template fill; regenerate the golden fixture"
    )
