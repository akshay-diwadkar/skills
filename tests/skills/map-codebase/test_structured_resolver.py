"""Exact behavior tests for structured resolver intent and selection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import _scoped_source_terms, discover_candidates, render_context, resolve_task, retrieve_evidence
from resolver.confidence import assess_confidence
from resolver.features import subsystem_tokens
from resolver.query_parser import parse_task_query
from resolver.scoring import score_candidates


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


def test_contrastive_gerunds_and_change_impact_are_parsed() -> None:
    query = parse_task_query(
        "If tenant routing changes, identify the implementation and direct test, "
        "excluding generated clients and ignoring legacy documentation."
    )

    assert "impact" in query.intents
    assert query.excluded_component_types == frozenset(
        {"client", "documentation", "generated", "legacy"}
    )


def test_admission_and_routing_language_infers_pipeline_components() -> None:
    assert parse_task_query(
        "Where are incoming messages validated before admission?"
    ).requested_component_type == "receiver"
    assert parse_task_query(
        "Where is tenant routing applied before delivery?"
    ).requested_component_type == "processor"
    assert parse_task_query(
        "Which control-plane policy selects a tenant exporter route?"
    ).requested_component_type == "policy"
    assert parse_task_query(
        "Where does the distribution reject duplicate receiver registrations?"
    ).requested_component_type == "distribution"
    persistence = parse_task_query("Locate the SQLite adapter that persists pending events")
    assert persistence.requested_component_type == "adapter"
    assert persistence.requested_layer == "persistence"
    assert parse_task_query("Where is refund eligibility bounded by the settled amount?").requested_component_type == "policy"


def test_change_impact_returns_direct_test_in_phase_three_only(tmp_path: Path) -> None:
    source = tmp_path / "src"
    tests = tmp_path / "tests"
    source.mkdir()
    tests.mkdir()
    (source / "tenant_router.py").write_text(
        "def route_tenant(tenant: str) -> str:\n"
        "    return f'partition:{tenant}'\n",
        encoding="utf-8",
    )
    (tests / "test_tenant_router.py").write_text(
        "from src.tenant_router import route_tenant\n\n"
        "def test_routes_tenant_partition():\n"
        "    assert route_tenant('north') == 'partition:north'\n",
        encoding="utf-8",
    )
    output = _build(tmp_path)
    task = "If tenant routing changes, identify the implementation and direct test."

    phase_two = resolve_task(tmp_path, task, output, phase=2)["targets"]
    phase_three = resolve_task(tmp_path, task, output, phase=3)["targets"]

    assert phase_two == []
    assert [target["path"] for target in phase_three] == ["tests/test_tenant_router.py"]


def test_domain_layer_request_prefers_a_domain_path_over_an_api_neighbor(tmp_path: Path) -> None:
    domain = tmp_path / "src" / "domain"
    api = tmp_path / "src" / "api"
    domain.mkdir(parents=True)
    api.mkdir(parents=True)
    (domain / "invoice_pricing.py").write_text(
        "def price_invoice(subtotal: int, tax: int) -> int:\n"
        "    return subtotal + tax\n",
        encoding="utf-8",
    )
    (api / "invoice_endpoint.py").write_text(
        "def price_invoice_request(subtotal: int, tax: int) -> int:\n"
        "    return subtotal + tax\n",
        encoding="utf-8",
    )
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Which domain pricing function calculates invoice tax?", output)

    assert result["primary_owner"]["path"] == "src/domain/invoice_pricing.py"


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


def test_staged_discovery_and_evidence_are_bounded_and_immutable(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "owner.py").write_text("def route_tenant(tenant: str) -> str:\n    return tenant\n", encoding="utf-8")
    output = _build(tmp_path)
    import json

    from knowledge.config import load_config
    from resolve_task import _signals
    from resolver.query_parser import parse_task_query

    repo = json.loads((output / "repo-map.json").read_text(encoding="utf-8"))
    catalog = json.loads((output / "symbols.json").read_text(encoding="utf-8"))
    index = json.loads((output / "symbol-index.json").read_text(encoding="utf-8"))
    query = parse_task_query("Which processor routes a tenant?")
    discovery = discover_candidates(
        repo["files"], index, _signals("Which processor routes a tenant?"), query,
        weights=load_config(tmp_path)["weights"],
        freshness="fresh", configuration_keys={},
    )
    evidence = retrieve_evidence(tmp_path, output, catalog, discovery.candidate_paths)
    assert "src/owner.py" in discovery.candidate_paths
    assert isinstance(evidence.source_terms_by_path["src/owner.py"], frozenset)
    assert render_context({"status": "abstain"}) == {"status": "abstain"}


def test_unrequested_generated_and_legacy_surfaces_cannot_be_primary_owners() -> None:
    query = parse_task_query("Which receiver validates the tenant protocol?")
    candidates = [
        {"file": {"path": "generated/receiver.ts", "role": "source", "generated": True}, "score": 80, "evidence": {}},
        {"file": {"path": "compatibility/legacy_receiver.py", "role": "source", "component_types": ["legacy"]}, "score": 80, "evidence": {}},
    ]
    assert score_candidates(candidates, {}, query) == []


def test_untracked_surface_requires_an_explicit_request() -> None:
    candidate = {
        "file": {"path": "scratch/tenant_receiver.py", "role": "source", "tracked": False},
        "score": 80,
        "evidence": {},
    }
    ordinary = parse_task_query("Which receiver validates a tenant?")
    explicit = parse_task_query("Which untracked receiver validates a tenant?")
    assert score_candidates([candidate], {}, ordinary) == []
    assert score_candidates([candidate], {}, explicit)


def test_exact_path_evidence_outranks_fuzzy_candidate() -> None:
    query = parse_task_query("Update src/services/component_010.py directly")
    candidates = [
        {"file": {"path": "src/services/component_001.py", "role": "source"}, "score": 80, "evidence": {}},
        {"file": {"path": "src/services/component_010.py", "role": "source"}, "score": 1, "evidence": {}},
    ]

    ranked = score_candidates(candidates, {}, query, exact_paths={"src/services/component_010.py"})

    assert ranked[0]["file"]["path"] == "src/services/component_010.py"
    assert "exact_path: src/services/component_010.py" in ranked[0]["direct_evidence"]


def test_path_features_normalize_windows_separators() -> None:
    assert "billing" in subsystem_tokens({"path": r"src\\billing\\adapter.py"})


def test_no_ripgrep_fallback_finds_late_admitted_source_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "src" / "owner.py"
    path.parent.mkdir()
    path.write_text("\n".join(["pass"] * 300 + ["def resolve_tenant(): pass"]), encoding="utf-8")

    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise OSError("rg unavailable")

    monkeypatch.setattr("resolve_task.subprocess.run", unavailable)
    evidence = _scoped_source_terms(tmp_path, frozenset({"src/owner.py"}), {"tenant"})

    assert any(token.startswith("tenant") for token in evidence["src/owner.py"])
