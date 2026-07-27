from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVALS = Path(__file__).with_name("evals")
SPEC = importlib.util.spec_from_file_location(
    "run_decision_quality_ab", EVALS / "run_decision_quality_ab.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_decision_quality_rubric_scores_root_fix_and_hidden_consumers() -> None:
    metadata = (
        '<!-- plan-metadata: {"provisional":{"intent":"bug-fix","risk_domains":[],"tier":"standard",'
        '"tier_signals":[]},"final":{"intent":"bug-fix","risk_domains":[],"tier":"standard","tier_signals":[]}} -->'
    )
    plan = f"""# Decimal parsing
<!-- plan-contract: 5 -->
{metadata}

## Outcome and Scope
## Evidence Ledger
- F-1: kind: documentation-contract | path: src/amount.ts | lines: 1-3 | anchor: parseAmount | excerpt-sha256: x | file-sha256: y | observation: Number.parseInt truncates decimal input
- F-2: kind: documentation-contract | path: src/index.ts | lines: 1-1 | anchor: parseAmount | excerpt-sha256: x | file-sha256: y | observation: re-export
- F-3: kind: documentation-contract | path: src/invoice.ts | lines: 1-5 | anchor: parseAmount | excerpt-sha256: x | file-sha256: y | observation: consumer
## Decisions
- D-1: selected: use Number raw parsing for decimal preservation | evidence: F-1 | rejected: patch invoice multiplication | drawback: invalid values remain numeric errors
## Implementation Specification
- CH-1: path: src/amount.ts | anchor: parseAmount | status: existing | locality: local-production | reversibility: reversible | evidence: F-1 | change: replace integer parsing with decimal preserving conversion
- CH-2: path: tests/amount.test.ts | anchor: parseAmount | status: existing | locality: test-only | reversibility: reversible | evidence: F-1 | change: add exact decimal and whole number expectations
## Propagation Record
- P-1: owner: CH-1 | because: F-2 | surface: re-export | disposition: unchanged
- P-2: owner: CH-1 | because: F-3 | surface: transitive-consumer | disposition: unchanged
## Boundary Traces
## Domain Obligations
## Traceability
## Verification
## Risks, Assumptions, and Attack
"""
    rubric = json.loads(MODULE.RUBRIC.read_text(encoding="utf-8"))
    score = MODULE.score_decision_quality(plan, rubric)
    assert score["score"] == 100
    assert score["failed_checks"] == []


def test_provider_neutral_ab_runner_isolates_skill_conditions_and_model_pairs(
    tmp_path: Path,
) -> None:
    adapter = tmp_path / "adapter.py"
    log = tmp_path / "requests.jsonl"
    adapter.write_text(
        "import json, sys\n"
        "request = json.load(sys.stdin)\n"
        "with open(sys.argv[1], 'a', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps(request) + '\\n')\n"
        "print(json.dumps({'plan_markdown': 'not a v5 plan'}))\n",
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    report = MODULE.evaluate(
        [sys.executable, str(adapter), str(log)],
        "weaker-model",
        "stronger-model",
        output,
    )
    requests = [
        json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(requests) == 4
    assert {request["capability"] for request in requests} == {"weaker", "stronger"}
    for request in requests:
        if request["condition"] == "with-skill":
            assert request["load_skill"] is True
            assert request["skill_root"] == str(MODULE.SKILL_ROOT)
        else:
            assert request["load_skill"] is False
            assert request["skill_root"] is None
    assert len(report["paired_deltas"]) == 2
    assert report["aggregate_deltas"] == {
        "schema_grounding": 0,
        "decision_quality": 0,
    }
    assert output.is_file()
