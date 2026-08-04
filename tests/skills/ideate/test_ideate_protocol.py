from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "research" / "ideate"


def _valid_draft_text() -> str:
    return (
        "# Ideas: reduce latency\n\n"
        "## 1. Handoff\n"
        "- State: decision-ready\n"
        "- Goal: reduce latency\n"
        "- Success measure: p99 < 200ms\n"
        "- Baseline / status quo: p99 = 500ms\n"
        "- Scope: API layer\n"
        "- Non-goals: database\n"
        "- Assumptions: current p99 = 500 ms\n"
        "- Material unknowns: none\n"
        "- Decision horizon: Q3 2026\n"
        "- Decision criteria: latency, effort\n"
        "- Selected source playbooks: software/engineering\n"
        "- Research coverage: docs\n"
        "- Research limitations: none\n"
        "- Research stop condition: stop after 5 sources or 30 minutes\n"
        "- Research stop reason: condition met\n\n"
        "## 2. Evidence\n\n"
        "### External evidence\n\n"
        "External research status: completed\n\n"
        "| ID | Finding | Source | Locator | Date/freshness | Relevance |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| E1 | Caching helps | https://example.com | § 1 | 2026-07 | high |\n\n"
        "## 3. Candidate ideas\n\n"
        "### I1. Add cache\n"
        "- Mechanism: cache responses\n"
        "- Mechanism category: caching\n"
        "- Why it applies: E1 says so\n"
        "- Evidence: E1 finding\n"
        "- Support basis: evidence-backed: E1\n"
        "- Decision-criteria fit: best on latency\n"
        "- Expected impact: high\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: low\n"
        "- Risk: low\n"
        "- Confidence: moderate\n"
        "- What would disconfirm it: low hit rate\n"
        "- Cheapest decisive experiment: shadow cache; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n\n"
        "### I2. Compress\n"
        "- Mechanism: gzip\n"
        "- Mechanism category: compression\n"
        "- Why it applies: saves bytes\n"
        "- Evidence: E1 finding\n"
        "- Support basis: evidence-backed: E1\n"
        "- Decision-criteria fit: good on effort\n"
        "- Expected impact: medium\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: low\n"
        "- Risk: low\n"
        "- Confidence: low\n"
        "- What would disconfirm it: negligible size\n"
        "- Cheapest decisive experiment: benchmark; metric: size; pass/fail: >20%; duration: 1d; cost/effort: low\n\n"
        "### I3. Pool connections\n"
        "- Mechanism: reuse\n"
        "- Mechanism category: pooling\n"
        "- Why it applies: overhead\n"
        "- Evidence: E1 finding\n"
        "- Support basis: hypothesis\n"
        "- Decision-criteria fit: weakest on effort\n"
        "- Expected impact: medium\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: high\n"
        "- Risk: medium\n"
        "- Confidence: low\n"
        "- What would disconfirm it: no overhead\n"
        "- Cheapest decisive experiment: profile; metric: time; pass/fail: <10ms; duration: 1d; cost/effort: medium\n\n"
        "## 4. Comparison\n\n"
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | low | low | low | moderate |\n"
        "| 3 | I3 | medium | high | medium | low | weak |\n\n"
        "## 5. Recommendation\n"
        "- Provisional lead: I1 — Add cache\n"
        "- Why it leads: best ratio\n"
        "- Why it beats rank 2: lower effort\n"
        "- Cheapest decisive experiment: shadow cache; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n"
        "- What could change the ranking: hit rate data\n"
        "- Conditions that would change the ranking: hit rate < 20%\n"
        "- How decision criteria were applied: latency dominated, then effort broke the tie\n\n"
        "## 6. Contradictions and open questions\n"
        "- Strongest challenge to rank 1: cache misses\n"
        "- Baseline / status quo comparison: better than baseline\n"
        "- Condition for a different winner: rank 2 wins if size dominates\n"
        "- Remaining contradiction or uncertainty: none remaining \u2014 same dataset\n"
    )


def test_doctor_succeeds(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(tmp_path),
            "--format", "json",
            "doctor",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data.get("status") == "ready"


def test_stateless_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft_text(), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(repo),
            "--input", f"draft={draft}",
            "--input", f"output_dir={output}",
            "--format", "json",
            "run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data.get("status") == "complete"


def test_missing_input_draft(tmp_path: Path) -> None:
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(tmp_path),
            "--input", f"output_dir={output}",
            "--format", "json",
            "run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_invocation_metadata() -> None:
    import re
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "disable-model-invocation: false" in skill_md
    assert "user-invocable: true" in skill_md
    version_m = re.search(r"^version:\s*(.+)$", skill_md, re.MULTILINE)
    assert version_m is not None
    assert version_m.group(1).strip() == "2.0.0"


def test_vendored_runtime_matches_canonical() -> None:
    canonical = ROOT / "tools" / "skill_protocol" / "runtime.py"
    vendored = SKILL / "scripts" / "_skill_protocol_runtime.py"
    assert canonical.is_file(), "canonical runtime missing"
    assert vendored.is_file(), "vendored runtime missing"
    assert canonical.read_bytes() == vendored.read_bytes(), "vendored runtime is stale"


def test_vendored_diagnostics_matches_canonical() -> None:
    canonical = ROOT / "tools" / "diagnostics" / "runtime.py"
    vendored = SKILL / "scripts" / "_diagnostic_contract.py"
    assert canonical.is_file(), "canonical diagnostic runtime missing"
    assert vendored.is_file(), "vendored diagnostic missing"
    assert canonical.read_bytes() == vendored.read_bytes(), "vendored diagnostics is stale"
