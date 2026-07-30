"""Exact behavior tests for structured resolver intent and selection."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import resolve_task
from resolver.confidence import assess_confidence
from resolver.query_parser import parse_task_query


def _build(root: Path) -> Path:
    output = root / ".agent" / "knowledge"
    build_knowledge(root, output)
    return output


def test_contrastive_query_parses_requested_and_excluded_dimensions() -> None:
    query = parse_task_query(
        "Find the notification job owner, not billing orchestration; "
        "current implementation, not legacy/generated code"
    )

    assert query.requested_subsystem == "notification"
    assert query.requested_component_type == "job"
    assert query.excluded_subsystem == "billing"
    assert query.excluded_component_types == frozenset({"generated", "legacy", "orchestrator"})
    assert query.excluded_roles == frozenset()


def test_phase_one_returns_one_owner_and_separate_alternative(tmp_path: Path) -> None:
    jobs = tmp_path / "src" / "notifications"
    billing = tmp_path / "src" / "billing"
    jobs.mkdir(parents=True)
    billing.mkdir(parents=True)
    (jobs / "renewal_job.py").write_text(
        "class RenewalNotificationJob:\n"
        "    def send_notification(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    (billing / "renewal_orchestrator.py").write_text(
        "class RenewalBillingOrchestrator:\n"
        "    def send_notification(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    output = _build(tmp_path)

    result = resolve_task(
        tmp_path,
        "Find the renewal notification job owner, not billing orchestration",
        output,
    )

    assert result["primary_owner"]["path"] == "src/notifications/renewal_job.py"
    assert result["targets"] == [result["primary_owner"]]
    assert result["co_owners"] == []
    assert all(item["path"] != result["primary_owner"]["path"] for item in result["alternatives"])


def test_multi_owner_requires_explicit_request(tmp_path: Path) -> None:
    src = tmp_path / "src" / "delivery"
    src.mkdir(parents=True)
    (src / "email_handler.py").write_text(
        "class EmailDeliveryHandler:\n"
        "    def deliver_notification(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    (src / "sms_handler.py").write_text(
        "class SmsDeliveryHandler:\n"
        "    def deliver_notification(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )
    output = _build(tmp_path)

    single = resolve_task(tmp_path, "Find the delivery handler owner", output)
    multiple = resolve_task(tmp_path, "Find all co-owners of the delivery handlers", output)

    assert len(single["targets"]) == 1
    assert single["co_owners"] == []
    assert len(multiple["targets"]) >= 1
    assert multiple["targets"][0] == multiple["primary_owner"]


def test_negative_conflict_prevents_resolved_confidence() -> None:
    candidate = {
        "score": 50.0,
        "negative_conflicts": 1,
        "component_match": True,
        "subsystem_match": True,
        "evidence": {
            "exact_symbol: Owner": (30.0, "symbol"),
            "component_type: service": (10.0, "component_type"),
        },
    }

    assessment = assess_confidence([candidate], freshness="fresh", focused=True)

    assert assessment.status == "ambiguous"
    assert assessment.level == "medium"
    assert assessment.negative_conflicts == 1


def test_scoring_modules_do_not_depend_on_benchmark_fixtures() -> None:
    resolver_root = SKILL_SCRIPTS / "resolver"
    forbidden = ("benchmarks", "adversarial_cases", "heldout_cases")

    for path in resolver_root.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert all(value not in content for value in forbidden), path.name
