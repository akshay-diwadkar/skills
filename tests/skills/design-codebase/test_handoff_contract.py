from __future__ import annotations

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
