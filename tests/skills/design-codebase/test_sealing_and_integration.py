from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "engineering" / "design-codebase" / "scripts"))

import _diagnostic_contract  # noqa: E402
import handoff_contract  # noqa: E402
import seal_assessment  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "design-codebase"
SEALER = SKILL / "scripts" / "seal_assessment.py"
SEAL_PLAN = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "seal_plan.py"


def make_repo(root: Path) -> Path:
    (root / "payments").mkdir(parents=True)
    (root / "checkout").mkdir()
    (root / "subscriptions").mkdir()
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
    (root / "subscriptions" / "renew.py").write_text(
        "from payments.service import charge_payment\n"
        "\n"
        "def renew(amount, payment_token):\n"
        "    return charge_payment(amount, 'USD', payment_token)\n",
        encoding="utf-8",
    )
    return root


def example() -> str:
    return (SKILL / "references" / "worked-examples.md").read_text(encoding="utf-8")


def seal_command(repo: Path, output: Path, draft: Path, *, json_output: bool = False) -> list[str]:
    command = [
        sys.executable,
        str(SEALER),
        "--repo-root",
        str(repo),
        "--output-dir",
        str(output),
    ]
    if json_output:
        command.extend(("--format", "json"))
    command.append(str(draft))
    return command


def test_sealer_emits_only_deterministic_handoff(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example().replace("\n", "\r\n"), encoding="utf-8")
    output = tmp_path / "output"
    command = seal_command(repo, output, draft)
    first = subprocess.run(command, capture_output=True, text=True, check=True)
    first_text = (output / "handoff.md").read_text(encoding="utf-8")
    second = subprocess.run(command, capture_output=True, text=True, check=True)

    assert Path(first.stdout.strip()) == output / "handoff.md"
    assert Path(second.stdout.strip()) == output / "handoff.md"
    assert {path.name for path in output.iterdir()} == {"handoff.md"}
    assert (output / "handoff.md").read_text(encoding="utf-8") == first_text
    assert "assessment-validation" not in first_text
    assert "design-assessment-contract" not in first_text


def test_sealer_backfills_all_local_evidence_hashes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    unhashed = re.sub(r" \| sha256: [0-9a-f]{64}", "", example())
    draft.write_text(unhashed, encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        seal_command(repo, output, draft),
        capture_output=True,
        text=True,
        check=True,
    )

    sealed = (output / "handoff.md").read_text(encoding="utf-8")
    assert sealed.count(" | sha256: ") == 4
    _parsed, diagnostics = handoff_contract.validate_handoff(
        sealed,
        repo,
        require_evidence_hashes=True,
    )
    assert diagnostics == []


def test_invalid_draft_writes_nothing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "invalid.md"
    draft.write_text(example().replace("## Problem & Scope", "## Missing"), encoding="utf-8")
    output = tmp_path / "output"
    result = subprocess.run(
        seal_command(repo, output, draft),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Cannot seal invalid design handoff" in result.stderr
    assert not output.exists()


def test_invalid_draft_preserves_existing_artifact_without_write_attempt(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "invalid.md"
    draft.write_text(example().replace("## Problem & Scope", "## Missing"), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    destination = output / "handoff.md"
    destination.write_text("existing sealed artifact\n", encoding="utf-8")

    with patch.object(seal_assessment, "_write_atomic") as write_atomic:
        result = seal_assessment.main(
            [
                "--repo-root",
                str(repo),
                "--output-dir",
                str(output),
                str(draft),
            ]
        )

    assert result == 1
    write_atomic.assert_not_called()
    assert destination.read_text(encoding="utf-8") == "existing sealed artifact\n"


def test_stale_supplied_hash_writes_nothing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "stale.md"
    draft.write_text(example(), encoding="utf-8")
    (repo / "payments" / "service.py").write_text(
        (repo / "payments" / "service.py").read_text(encoding="utf-8").replace(
            "return provider_sdk.charge(request)",
            "return provider_sdk.charge(request, retry=True)",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    result = subprocess.run(
        seal_command(repo, output, draft),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "evidence.sha256.mismatch" in result.stderr
    assert not output.exists()


def test_sealer_json_failure_is_canonical(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "invalid.md"
    draft.write_text(example().replace("## Problem & Scope", "## Missing"), encoding="utf-8")
    result = subprocess.run(
        seal_command(repo, tmp_path / "unused", draft, json_output=True),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    diagnostics = json.loads(result.stdout)
    assert diagnostics
    assert all(_diagnostic_contract.is_canonical(item) for item in diagnostics)


def test_handoff_is_a_valid_plan_change_v6_request_file(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example(), encoding="utf-8")
    output = tmp_path / "design-output"
    subprocess.run(
        seal_command(repo, output, draft),
        capture_output=True,
        text=True,
        check=True,
    )

    handoff = output / "handoff.md"
    plan = tmp_path / "plan.md"
    plan.write_text(
        """# Introduce a payment gateway boundary

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: checkout and renewal payment callers | when: charging moves behind a gateway | then: callers use the shared gateway contract | unchanged: provider decline behavior remains stable

## Evidence
F-1: kind: source | path: payments/service.py | lines: 1-7 | anchor: charge_payment | claim: charge_payment owns provider request construction and charging

## Implementation
CH-1: path: payments/service.py | anchor: charge_payment | status: existing | evidence: F-1 | change: introduce the selected PaymentGateway charge boundary while preserving provider error behavior | locality: shared | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: checkout and renewal payment scenarios | when: targeted payment tests execute | then: both callers use the gateway and preserve decline behavior | command: python -m pytest tests/test_checkout.py -q
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SEAL_PLAN),
            "--repo-root",
            str(repo),
            "--request-file",
            str(handoff),
            "--draft",
            str(plan),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    handoff_text = handoff.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(re.search(r"<!-- plan-proof: (.+) -->", result.stdout).group(1))  # type: ignore[union-attr]
    assert proof["binding"]["request_sha256"] == hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
    assert "PaymentGateway.charge" in handoff_text
    assert "Error surface direction: shrink" in handoff_text
    assert not list(tmp_path.rglob("baseline.json"))
    assert not list(tmp_path.rglob("inventory.json"))


def test_sealer_reports_source_mutation_before_handoff(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example(), encoding="utf-8")
    output = tmp_path / "design-output"
    subprocess.run(
        seal_command(repo, output, draft),
        capture_output=True,
        text=True,
        check=True,
    )
    handoff = output / "handoff.md"
    fresh = subprocess.run(
        seal_command(repo, tmp_path / "verify-output", handoff),
        capture_output=True,
        text=True,
    )
    assert fresh.returncode == 0, fresh.stderr

    source = repo / "checkout" / "process.py"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "return charge_payment(amount, 'USD', token)",
            "return charge_payment(amount, 'EUR', token)",
        ),
        encoding="utf-8",
    )
    stale = subprocess.run(
        seal_command(repo, tmp_path / "stale-output", handoff, json_output=True),
        capture_output=True,
        text=True,
    )
    assert stale.returncode == 1
    diagnostics = json.loads(stale.stdout)
    assert any(item["code"] == "evidence.sha256.mismatch" for item in diagnostics)
    assert any("checkout/process.py:1-6" in item["message"] for item in diagnostics)


def test_seal_handoff_is_one_pass_and_caches_local_evidence(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    text = example().replace(
        "- [E-5] source: code | locator: subscriptions/renew.py:1-4 | anchor: renew | sha256: 62ff00c332b7013d83e706504014f2ea6e552adb83fa6bb16f63a9ac11ab3b2a | claim:",
        "- [E-5] source: code | locator: payments/service.py:3-7 | anchor: charge_payment | claim:",
    )
    section_calls = 0
    evidence_calls = 0
    reads: list[Path] = []
    hashes = 0
    original_sections = handoff_contract._parse_sections
    original_evidence = handoff_contract._parse_evidence
    original_read_text = Path.read_text
    original_hash = handoff_contract.excerpt_sha256

    def count_sections(value: str):
        nonlocal section_calls
        section_calls += 1
        return original_sections(value)

    def count_evidence(body: str, full_text: str):
        nonlocal evidence_calls
        evidence_calls += 1
        return original_evidence(body, full_text)

    def count_read(path: Path, *args, **kwargs):
        reads.append(path.resolve())
        return original_read_text(path, *args, **kwargs)

    def count_hash(lines: list[str], start: int, end: int) -> str:
        nonlocal hashes
        hashes += 1
        return original_hash(lines, start, end)

    with (
        patch.object(handoff_contract, "_parse_sections", side_effect=count_sections),
        patch.object(handoff_contract, "_parse_evidence", side_effect=count_evidence),
        patch.object(Path, "read_text", new=count_read),
        patch.object(handoff_contract, "excerpt_sha256", side_effect=count_hash),
    ):
        _parsed, diagnostics, sealed = handoff_contract.seal_handoff(text, repo)

    assert diagnostics == []
    assert section_calls == 1
    assert evidence_calls == 1
    assert len(reads) == 3
    assert len(set(reads)) == 3
    assert hashes == 4
    assert sealed.count(" | sha256: ") == 4
