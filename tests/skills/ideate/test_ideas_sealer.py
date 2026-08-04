from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "research" / "ideate"


# ---------------------------------------------------------------------------
# Minimal valid draft factory
# ---------------------------------------------------------------------------


def _valid_draft() -> str:
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
        "- Research coverage: docs, benchmarks\n"
        "- Research limitations: none\n\n"
        "## 2. Evidence\n\n"
        "### External evidence\n\n"
        "External research status: completed\n\n"
        "| ID | Finding | Source | Locator | Date/freshness | Relevance |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| E1 | Caching cuts latency | https://example.com | § 2 | 2026-07 | high |\n\n"
        "## 3. Candidate ideas\n\n"
        "### I1. Add cache\n"
        "- Mechanism: cache responses\n"
        "- Mechanism category: caching\n"
        "- Why it applies: E1 shows 50% reduction\n"
        "- Evidence: E1\n"
        "- Expected impact: high\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: low\n"
        "- Risk: low\n"
        "- Confidence: moderate\n"
        "- What would disconfirm it: cache hit rate < 20%\n"
        "- Cheapest decisive experiment: run 1-day shadow cache; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n\n"
        "### I2. Reduce payload\n"
        "- Mechanism: compress JSON\n"
        "- Mechanism category: compression\n"
        "- Why it applies: E1 secondary finding\n"
        "- Evidence: E1\n"
        "- Expected impact: medium\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: medium\n"
        "- Risk: low\n"
        "- Confidence: low\n"
        "- What would disconfirm it: < 10% size reduction\n"
        "- Cheapest decisive experiment: benchmark gzip; metric: size; pass/fail: >20%; duration: 1d; cost/effort: low\n\n"
        "### I3. Connection pooling\n"
        "- Mechanism: reuse connections\n"
        "- Mechanism category: pooling\n"
        "- Why it applies: E1 mentions pool overhead\n"
        "- Evidence: E1\n"
        "- Expected impact: medium\n"
        "- Assumptions and dependencies: none\n"
        "- Effort: high\n"
        "- Risk: medium\n"
        "- Confidence: low\n"
        "- What would disconfirm it: no connection overhead\n"
        "- Cheapest decisive experiment: profile connection setup; metric: setup time; pass/fail: <10ms; duration: 1d; cost/effort: medium\n\n"
        "## 4. Comparison\n\n"
        "| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | I1 | high | low | low | moderate | strong |\n"
        "| 2 | I2 | medium | medium | low | low | moderate |\n"
        "| 3 | I3 | medium | high | medium | low | moderate |\n\n"
        "## 5. Recommendation\n"
        "- Provisional lead: I1 — Add cache\n"
        "- Why it leads: highest impact, lowest effort\n"
        "- Why it beats rank 2: lower effort than compression\n"
        "- Cheapest decisive experiment: run 1-day shadow cache; metric: hit rate; pass/fail: >50%; duration: 1d; cost/effort: low\n"
        "- What could change the ranking: cache hit rate data\n"
        "- Conditions that would change the ranking: hit rate < 20%\n\n"
        "## 6. Contradictions and open questions\n"
        "- None identified.\n"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seals_valid_ideas_md(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "seal_ideas.py"),
            "--repo-root",
            str(repo),
            "--draft",
            str(draft),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "sealed"
    assert Path(data["path"]).name == "ideas.md"


def test_receipt_digest_matches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        check=True, capture_output=True,
    )
    sealed = (output / "ideas.md").read_text(encoding="utf-8")
    first, _, body = sealed.partition("\n")
    assert first.startswith("<!-- ideas-handoff: 1; sha256: ")
    digest = first.split("sha256: ")[1].rstrip(" -->")
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == digest


def test_valid_reseal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        check=True, capture_output=True,
    )
    sealed_path = output / "ideas.md"
    sealed_text = sealed_path.read_text(encoding="utf-8")
    draft2 = tmp_path / "draft2.md"
    draft2.write_text(sealed_text, encoding="utf-8")
    output2 = tmp_path / "output2"
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft2), "--output-dir", str(output2)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "sealed"
    assert (output2 / "ideas.md").read_text(encoding="utf-8") == sealed_path.read_text(encoding="utf-8")


def test_mismatched_receipt_rejection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        check=True, capture_output=True,
    )
    sealed_path = output / "ideas.md"
    sealed_text = sealed_path.read_text(encoding="utf-8")
    tampered = sealed_text + "\n<!-- extra line -->\n"
    tampered_draft = tmp_path / "tampered.md"
    tampered_draft.write_text(tampered, encoding="utf-8")
    output2 = tmp_path / "output2"
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(tampered_draft), "--output-dir", str(output2)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0 or "error" in result.stdout.lower() or "diagnostics" in result.stdout


def test_deterministic_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output1 = tmp_path / "output1"
    output2 = tmp_path / "output2"
    for out in (output1, output2):
        subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
             "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(out)],
            check=True, capture_output=True,
        )
    assert (output1 / "ideas.md").read_bytes() == (output2 / "ideas.md").read_bytes()


def test_no_partial_output_on_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text("# Ideas: test\n\n## 1. Handoff\n- State: decision-ready\n", encoding="utf-8")
    output = tmp_path / "output"
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert not (output / "ideas.md").exists()


def test_atomic_replacement_after_correction(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        check=True, capture_output=True,
    )
    original = (output / "ideas.md").read_bytes()
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout)["status"] == "sealed"
    assert (output / "ideas.md").read_bytes() == original


def test_rejects_extra_artifacts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    (output / "extra.txt").write_text("unexpected", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert (output / "extra.txt").exists()


def test_no_workspace_writes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "existing.py").write_text("# existing\n", encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_ideas.py"),
         "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output)],
        check=True, capture_output=True,
    )
    assert {p.name for p in repo.iterdir()} == {"existing.py"}


# ---------------------------------------------------------------------------
# Requirement §5 Workspace Write Guard Tests
# ---------------------------------------------------------------------------


def test_rejects_output_inside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft(), encoding="utf-8")
    output_inside = repo / "ideas_output"

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "seal_ideas.py"),
            "--repo-root", str(repo),
            "--draft", str(draft),
            "--output-dir", str(output_inside),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    data = json.loads(result.stdout)
    assert "ideas.output_in_workspace" in str(data)
    assert not (output_inside / "ideas.md").exists()


def test_rejects_draft_inside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft_inside = repo / "draft.md"
    draft_inside.write_text(_valid_draft(), encoding="utf-8")
    output = tmp_path / "output"

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "seal_ideas.py"),
            "--repo-root", str(repo),
            "--draft", str(draft_inside),
            "--output-dir", str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    data = json.loads(result.stdout)
    assert "ideas.draft_in_workspace" in str(data)
    assert not (output / "ideas.md").exists()
