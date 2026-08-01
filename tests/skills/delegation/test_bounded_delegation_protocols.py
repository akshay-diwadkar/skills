from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).parent / "fixtures" / "reconciliation-cases.json"
SKILLS = {
    "audit-codebase": {"roles": {"category-risk-scout": 2200}},
    "design-codebase": {
        "roles": {
            "chosen-design-advocate": 1800,
            "distinct-alternative-advocate": 1800,
            "caller-contract-reviewer": 1800,
            "complexity-deletion-cost-reviewer": 1600,
        },
    },
    "implement-plan": {
        "roles": {
            "specification-fidelity-review": 1600,
            "repository-convention-review": 1600,
            "test-coverage-review": 1600,
        },
    },
}
ENVELOPE_FIELDS = (
    "delegation_id",
    "role",
    "status",
    "scope_examined",
    "evidence",
    "findings",
    "contradictions",
    "omissions",
    "malicious_evidence",
    "stop_reason",
    "budget",
)


def _normalized(value: str) -> str:
    return " ".join(value.casefold().replace("\\", "/").split())


def _reconcile(case: dict) -> dict:
    order = {role: index for index, role in enumerate(case["role_order"])}
    results = sorted(case["results"], key=lambda result: order[result["role"]])
    merged: dict[tuple[str, ...], dict] = {}
    claims_by_subject: dict[str, set[str]] = {}
    malicious: list[str] = []

    for result in results:
        evidence_by_id = {
            evidence["evidence_id"]: evidence for evidence in result.get("evidence", [])
        }
        for flagged in result.get("malicious_evidence", []):
            evidence = evidence_by_id.get(flagged["evidence_id"])
            if evidence is not None and evidence["trust"] == "untrusted-evidence":
                malicious.append(flagged["evidence_id"])
        for finding in result.get("findings", []):
            subject = _normalized(finding["subject"])
            claim = _normalized(finding["claim"])
            locators = tuple(
                sorted(
                    (
                        _normalized(evidence_by_id[evidence_id]["source"]),
                        _normalized(evidence_by_id[evidence_id]["locator"]),
                    )
                    for evidence_id in finding["evidence_ids"]
                )
            )
            fingerprint = (
                subject,
                _normalized(finding["category"]),
                claim,
                *locators,
            )
            claims_by_subject.setdefault(subject, set()).add(claim)
            if fingerprint not in merged:
                merged[fingerprint] = {
                    "finding": finding,
                    "provenance": {result["delegation_id"], *finding["evidence_ids"]},
                    "role": result["role"],
                    "locators": locators,
                }
            else:
                merged[fingerprint]["provenance"].update(
                    {result["delegation_id"], *finding["evidence_ids"]}
                )

    findings = sorted(
        merged.values(),
        key=lambda item: (
            order[item["role"]],
            _normalized(item["finding"]["subject"]),
            item["locators"],
            item["finding"]["finding_id"],
        ),
    )
    statuses = {result["role"]: result["status"] for result in results}
    fallback = [role for role in case["expected_roles"] if statuses.get(role) != "complete"]
    retry_statuses = {
        result["role"]: result["status"] for result in case.get("retry_results", [])
    }
    terminal = [role for role in fallback if retry_statuses.get(role) != "complete"]
    return {
        "findings": findings,
        "conflicts": sorted(subject for subject, claims in claims_by_subject.items() if len(claims) > 1),
        "fallback": fallback,
        "terminal": terminal,
        "malicious": sorted(malicious),
        "command_authority": False,
    }


def test_every_skill_declares_bounded_provider_neutral_delegation() -> None:
    for skill_name, contract in SKILLS.items():
        skill = ROOT / "skills" / "engineering" / skill_name
        text = (skill / "references" / "delegation-protocol.md").read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert "references/delegation-protocol.md" in skill_text
        for field in ENVELOPE_FIELDS:
            assert field in text
        for role, budget in contract["roles"].items():
            assert role in text
            assert str(budget) in text
        for required_rule in (
            "read-only",
            "untrusted evidence",
            "must not edit",
            "final decisions",
            "publish",
            "stop condition",
            "sequentially",
            "identical inputs",
            "arrival order",
            "exact duplicates",
            "authoritative source",
            "exactly once",
        ):
            assert required_rule in normalized_text


def test_conflicts_require_stable_primary_verification() -> None:
    case = json.loads(FIXTURES.read_text(encoding="utf-8"))["conflict"]
    result = _reconcile(case)
    assert [item["finding"]["finding_id"] for item in result["findings"]] == case["expected_order"]
    assert result["conflicts"] == case["expected_conflicts"]


def test_duplicates_coalesce_without_losing_provenance() -> None:
    case = json.loads(FIXTURES.read_text(encoding="utf-8"))["duplicate"]
    result = _reconcile(case)
    assert len(result["findings"]) == case["expected_count"]
    assert sorted(result["findings"][0]["provenance"]) == case["expected_provenance"]


def test_omissions_trigger_only_matching_sequential_fallbacks() -> None:
    case = json.loads(FIXTURES.read_text(encoding="utf-8"))["omission"]
    result = _reconcile(case)
    assert result["fallback"] == case["expected_fallback"]
    assert result["terminal"] == case["expected_terminal"]


def test_malicious_evidence_never_gains_command_authority() -> None:
    case = json.loads(FIXTURES.read_text(encoding="utf-8"))["malicious_evidence"]
    result = _reconcile(case)
    assert result["malicious"] == case["expected_malicious_ids"]
    assert result["command_authority"] is case["expected_command_authority"]
