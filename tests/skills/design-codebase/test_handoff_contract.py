from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "design-codebase"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from handoff_contract import validate_handoff  # noqa: E402


def make_repo(root: Path) -> Path:
    (root / "payments").mkdir()
    (root / "checkout").mkdir()
    (root / "tests").mkdir()
    (root / "payments" / "service.py").write_text(
        "import provider_sdk\n"
        "\n"
        "def charge_payment(amount, currency, token=None):\n"
        "    request = provider_sdk.Request(amount, currency, token)\n"
        "    return provider_sdk.charge(request)\n"
        "\n"
        "PROVIDER_ERRORS = (provider_sdk.ProviderDeclined, provider_sdk.ProviderTimeout)\n",
        encoding="utf-8",
    )
    (root / "checkout" / "process.py").write_text(
        "from payments.service import charge_payment\n"
        "\n"
        "def checkout(amount, token=None):\n"
        "    try:\n"
        "        return charge_payment(amount, 'USD', token)\n"
        "    except TimeoutError:\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_checkout.py").write_text(
        "from checkout.process import checkout\n"
        "\n"
        "def test_checkout_decline():\n"
        "    result = checkout(10)\n"
        "    assert result is not None\n"
        "\n",
        encoding="utf-8",
    )
    return root


def example() -> str:
    return (SKILL / "references" / "worked-examples.md").read_text(encoding="utf-8")


def codes(text: str, repo: Path) -> set[str]:
    _parsed, diagnostics = validate_handoff(text, repo)
    return {diagnostic.code for diagnostic in diagnostics}


def test_worked_example_is_valid(tmp_path: Path) -> None:
    assert codes(example(), make_repo(tmp_path)) == set()


def test_worked_example_satisfies_section_specific_validation(tmp_path: Path) -> None:
    new_diagnostics = {
        "design.depth.unsubstantiated",
        "consolidation.reasoning.missing",
        "documentation.signature_restatement",
        "planner_questions.redecides_design",
    }
    assert codes(example(), make_repo(tmp_path)).isdisjoint(new_diagnostics)


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda text: text.replace("## Problem & Scope", "## Missing Problem"), "section.missing"),
        (
            lambda text: text.replace(
                "## Chosen Design & Depth Rationale",
                "## Problem & Scope\n\nDuplicated content [E-1]\n\n## Chosen Design & Depth Rationale",
            ),
            "section.duplicate",
        ),
            (
            lambda text: text.replace("## Problem & Scope", "## TEMPORARY", 1)
            .replace("## Chosen Design & Depth Rationale", "## Problem & Scope", 1)
            .replace("## TEMPORARY", "## Chosen Design & Depth Rationale", 1),
            "section.order",
        ),
        (
            lambda text: text.replace(
                "## Documentation Obligations\n\nCallers must know",
                "## Documentation Obligations\n\nTBD [E-2]\n\n## Ignored\n\nCallers must know",
            ),
            "section.content.invalid",
        ),
    ],
)
def test_sections_fail_closed(
    tmp_path: Path,
    mutator: Callable[[str], str],
    expected: str,
) -> None:
    repo = make_repo(tmp_path)
    assert expected in codes(mutator(example()), repo)


def test_each_section_requires_resolved_evidence(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    uncited = example().replace(
        "The design covers the synchronous charge contract and its caller-visible\n"
        "failures; settlement workflows and provider selection policy are outside this\n"
        "decision. [E-1] [E-2] [E-3]",
        "The design covers the synchronous charge contract and its caller-visible\n"
        "failures; settlement workflows and provider selection policy are outside this\n"
        "decision.",
    )
    assert "section.citation.missing" in codes(uncited, repo)
    undefined = example()
    last_citation = undefined.rfind("[E-4]")
    undefined = undefined[:last_citation] + "[E-99]" + undefined[last_citation + len("[E-4]") :]
    assert "section.citation.undefined" in codes(undefined, repo)


def test_evidence_identifiers_and_local_locators_are_validated(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    duplicate = example().replace(
        "## Problem & Scope",
        "- [E-1] source: request | locator: user-request | claim: A second claim that duplicates the identifier.\n\n"
        "## Problem & Scope",
    )
    assert "evidence.duplicate" in codes(duplicate, repo)
    assert "evidence.path.escape" in codes(
        example().replace("payments/service.py:1-7", "../outside.py:1-7"),
        repo,
    )
    assert "evidence.lines.invalid" in codes(
        example().replace("payments/service.py:1-7", "payments/service.py:1-99"),
        repo,
    )
    assert "evidence.anchor.missing" in codes(
        example().replace("anchor: charge_payment", "anchor: absent_symbol"),
        repo,
    )


def test_evidence_hashes_bind_exact_current_line_ranges(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert codes(example(), repo) == set()

    stale = example().replace(
        "383f9a66d5763c7a293a22f6388a418a7fba3f8979b35aa7c31fb404d0372c19",
        "0" * 64,
    )
    _parsed, diagnostics = validate_handoff(stale, repo)
    mismatch = next(item for item in diagnostics if item.code == "evidence.sha256.mismatch")
    assert "evidence is stale" in mismatch.message
    assert "payments/service.py:1-7" in mismatch.message

    malformed = example().replace(
        "383f9a66d5763c7a293a22f6388a418a7fba3f8979b35aa7c31fb404d0372c19",
        "A" * 64,
    )
    assert "evidence.sha256.invalid" in codes(malformed, repo)

    non_local = example().replace(
        "locator: user-request | claim:",
        f"locator: user-request | sha256: {'0' * 64} | claim:",
    )
    assert "evidence.sha256.unsupported" in codes(non_local, repo)


def test_evidence_hashes_are_optional_until_complete_verification(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    without_hashes = example()
    for digest in (
        "383f9a66d5763c7a293a22f6388a418a7fba3f8979b35aa7c31fb404d0372c19",
        "dcf982001e19cb93ac5b5bbf888233b985f8a933b53623ad2f71b3f1153f7e0d",
        "e5315c9858912d0b35c027fc7f9927dcb1cd0f266bc29b7f6d2d10cf3ac69e29",
    ):
        without_hashes = without_hashes.replace(f" | sha256: {digest}", "")

    assert codes(without_hashes, repo) == set()
    _parsed, diagnostics = validate_handoff(
        without_hashes,
        repo,
        require_evidence_hashes=True,
    )
    assert [item.code for item in diagnostics].count("evidence.sha256.missing") == 3


def test_evidence_hash_matches_plan_change_hash_excerpt(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    parsed, diagnostics = validate_handoff(example(), repo)
    assert diagnostics == []
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "hash_excerpt.py"),
            "--path",
            str(repo / "payments" / "service.py"),
            "--start-line",
            "1",
            "--end-line",
            "7",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    excerpt_hash = result.stdout.splitlines()[0].partition(": ")[2]
    assert parsed.evidence["E-2"].sha256 == excerpt_hash


def test_alternative_must_change_abstraction_and_boundary_or_owner(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    chosen_core = "PaymentGateway protocol using ChargeRequest, PaymentResult, and domain payment errors"
    same_core = example().replace(
        "Concrete payment-service module functions over provider SDK values",
        chosen_core,
    )
    assert "alternative.core.shared" in codes(same_core, repo)

    parameter_variant = (
        example()
        .replace(
            "Checkout and subscription flows call concrete functions owned by the payment service module",
            "Domain payment operations to provider integration",
        )
        .replace("- Owner: Payment service", "- Owner: Payments integration")
    )
    assert "alternative.structural.none" in codes(parameter_variant, repo)
    assert "alternative.structural.none" not in codes(example(), repo)


def test_fake_distinct_alternative_requires_distinct_evidence(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    fake_distinct = (
        example()
        .replace(
            "Checkout and subscription flows call concrete functions owned by the payment service module",
            "Provider integration boundary for domain payment operations",
        )
        .replace("- Owner: Payment service", "- Owner: Payment integration team")
        .replace(
            "Concrete payment-service module functions over provider SDK values",
            "Gateway protocol composed of charge request, result, and stable payment errors",
        )
        .replace(
            "less coherent boundary. [E-2] [E-3]",
            "less coherent boundary. [E-2] [E-4]",
        )
    )
    result_codes = codes(fake_distinct, repo)
    assert "alternative.structural.none" not in result_codes
    assert "alternative.no_distinct_evidence" in result_codes


@pytest.mark.parametrize("direction", ["shrink", "flat", "grow"])
def test_error_surface_directions_are_accepted(tmp_path: Path, direction: str) -> None:
    repo = make_repo(tmp_path)
    text = example().replace("Error surface direction: shrink", f"Error surface direction: {direction}")
    assert "interface.error_direction.invalid" not in codes(text, repo)
    assert "interface.error_growth.uncited" not in codes(text, repo)


def test_error_surface_growth_requires_cited_justification(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    invalid_direction = example().replace("Error surface direction: shrink", "Error surface direction: wider")
    assert "interface.error_direction.invalid" in codes(invalid_direction, repo)

    uncited_growth = (
        example()
        .replace("Error surface direction: shrink", "Error surface direction: grow")
        .replace(
            "provider-specific distinctions remain observable inside the integration boundary. [E-2] [E-4]",
            "provider-specific distinctions remain observable inside the integration boundary.",
        )
    )
    assert "interface.error_growth.uncited" in codes(uncited_growth, repo)


def test_generality_requires_two_patterns_or_an_intentionally_narrow_decision(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    one_pattern = example().replace(
        "Both need the same stable charge result and failure\n"
        "semantics despite different orchestration. If a third pattern required\n"
        "authorization without capture, the contract would add a distinct operation or\n"
        "request variant rather than expose provider SDK types. [E-2] [E-3]",
        "The checkout pattern needs the stable charge result. If a third pattern appeared,\n"
        "the contract would add a distinct operation rather than expose provider SDK types. [E-2]",
    )
    assert "generality.patterns.insufficient" in codes(one_pattern, repo)

    intentionally_narrow = one_pattern.replace(
        "The checkout pattern needs",
        "This design is intentionally narrow because only checkout needs",
    )
    assert "generality.patterns.insufficient" not in codes(intentionally_narrow, repo)


def test_depth_rationale_must_name_hidden_details_and_exposed_controls(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    restated_design = example().replace(
        "One charge operation and three domain types hide four provider concepts already used by independent callers, "
        "while callers retain every control that changes payment behavior. This has a higher functionality-to-interface "
        "ratio than exposing the SDK request and exception families directly. [E-2] [E-4]",
        "Callers submit a domain-owned `ChargeRequest` to `PaymentGateway.charge`; the integration owner translates "
        "provider requests, results, and exceptions. [E-2]",
    )
    assert "design.depth.unsubstantiated" in codes(restated_design, repo)


def test_consolidation_requires_structural_reasoning(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    generic = example().replace(
        "Consolidating checkout, subscription, and provider translation into the payment\n"
        "service was evaluated because the current code changes together around provider\n"
        "updates. It was rejected: provider translation is tightly coupled, but checkout\n"
        "and subscription policy have different owners and lifecycles. The chosen\n"
        "boundary consolidates only translation and error mapping. [E-2] [E-3]",
        "The implementation organization was reviewed and the selected approach appears preferable for future work. "
        "[E-2]",
    )
    assert "consolidation.reasoning.missing" in codes(generic, repo)


def test_documentation_must_add_knowledge_beyond_interface_rows(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    signature_restatement = example().replace(
        "Callers must know that the gateway owns provider timeout policy and error\n"
        "translation, that an idempotency key identifies one logical charge attempt, and\n"
        "that `PaymentUnavailable` does not prove the provider declined the charge.\n"
        "These semantics are not fully expressed by the signature and must be scheduled\n"
        "by `plan-change` as contract documentation. [E-2] [E-3]",
        "`PaymentGateway.charge(request: ChargeRequest) -> PaymentResult` uses an optional payment token and "
        "idempotency key, with `PaymentDeclined` and `PaymentUnavailable` as caller-visible errors. [E-2]",
    )
    assert "documentation.signature_restatement" in codes(signature_restatement, repo)


def test_planner_questions_must_not_reopen_chosen_design(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    redecides_owner = example().replace(
        "The design is complete. During grounding, the planner must reconcile the full\n"
        "caller inventory and identify which existing characterization tests own the\n"
        "provider-to-domain error mapping; those are implementation-scope questions, not\n"
        "design choices. [E-3] [E-4]",
        "During grounding, should Payments integration own the domain payment operations to provider integration "
        "boundary, or should the planner choose another core abstraction? [E-2]",
    )
    assert "planner_questions.redecides_design" in codes(redecides_owner, repo)


def test_handoff_requires_a_substantive_title(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert "title.invalid" in codes(example().replace("# Design Handoff:", "# Assessment:"), repo)
    assert "title.placeholder" in codes(
        example().replace(
            "# Design Handoff: Isolate Payment Provider Semantics",
            "# Design Handoff: TODO",
        ),
        repo,
    )
