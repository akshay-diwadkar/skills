from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "design-codebase"
FINALIZER = SKILL / "scripts" / "finalize_assessment.py"
CHECKER = SKILL / "scripts" / "check_assessment.py"
PREPARE_PLAN = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "prepare_plan.py"


def make_repo(root: Path) -> Path:
    (root / "payments").mkdir(parents=True)
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


def test_finalizer_emits_only_deterministic_handoff(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example().replace("\n", "\r\n"), encoding="utf-8")
    output = tmp_path / "output"
    command = [
        sys.executable,
        str(FINALIZER),
        "--repo-root",
        str(repo),
        "--output-dir",
        str(output),
        str(draft),
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=True)
    first_text = (output / "handoff.md").read_text(encoding="utf-8")
    second = subprocess.run(command, capture_output=True, text=True, check=True)

    assert Path(first.stdout.strip()) == output / "handoff.md"
    assert Path(second.stdout.strip()) == output / "handoff.md"
    assert {path.name for path in output.iterdir()} == {"handoff.md"}
    assert (output / "handoff.md").read_text(encoding="utf-8") == first_text
    assert "assessment-validation" not in first_text
    assert "design-assessment-contract" not in first_text


def test_finalizer_backfills_all_local_evidence_hashes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    unhashed = re.sub(r" \| sha256: [0-9a-f]{64}", "", example())
    draft.write_text(unhashed, encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--output-dir",
            str(output),
            str(draft),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    finalized = (output / "handoff.md").read_text(encoding="utf-8")
    assert finalized.count(" | sha256: ") == 3
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo),
            "--verify-evidence",
            str(output / "handoff.md"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_invalid_draft_writes_nothing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "invalid.md"
    draft.write_text(example().replace("## Problem & Scope", "## Missing"), encoding="utf-8")
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--output-dir",
            str(output),
            str(draft),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Cannot finalize invalid design handoff" in result.stderr
    assert not output.exists()


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
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--output-dir",
            str(output),
            str(draft),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "evidence.sha256.mismatch" in result.stderr
    assert not output.exists()


def test_checker_json_interface(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example(), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo),
            "--format",
            "json",
            str(draft),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == []


def test_checker_verify_evidence_requires_complete_hashes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(re.sub(r" \| sha256: [0-9a-f]{64}", "", example()), encoding="utf-8")
    base_command = [
        sys.executable,
        str(CHECKER),
        "--repo-root",
        str(repo),
        str(draft),
    ]
    assert subprocess.run(base_command, capture_output=True, text=True).returncode == 0
    verified = subprocess.run(
        [*base_command[:-1], "--verify-evidence", str(draft)],
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 1
    assert verified.stderr.count("evidence.sha256.missing") == 3


def test_handoff_is_a_valid_plan_change_request_file(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example(), encoding="utf-8")
    output = tmp_path / "design-output"
    subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--output-dir",
            str(output),
            str(draft),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    handoff = output / "handoff.md"
    run_dir = tmp_path / "plan-run"
    subprocess.run(
        [
            sys.executable,
            str(PREPARE_PLAN),
            "--repo-root",
            str(repo),
            "--request-file",
            str(handoff),
            "--run-dir",
            str(run_dir),
            "--tier",
            "standard",
            "--intent",
            "refactor",
            "--anchor",
            "payments/service.py:charge_payment",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    handoff_text = handoff.read_text(encoding="utf-8")
    inventory = json.loads((run_dir / "inventory.json").read_text(encoding="utf-8"))
    assert inventory["request_sha256"] == hashlib.sha256(handoff_text.encode("utf-8")).hexdigest()
    assert "PaymentGateway.charge" in handoff_text
    assert "Error surface direction: shrink" in handoff_text
    assert {path.name for path in run_dir.iterdir()} == {"baseline.json", "inventory.json", "draft.md"}


def test_verify_evidence_detects_source_mutation_before_handoff(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tmp_path / "draft.md"
    draft.write_text(example(), encoding="utf-8")
    output = tmp_path / "design-output"
    subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--repo-root",
            str(repo),
            "--output-dir",
            str(output),
            str(draft),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    handoff = output / "handoff.md"
    fresh = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo),
            "--verify-evidence",
            str(handoff),
        ],
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
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo),
            "--verify-evidence",
            str(handoff),
        ],
        capture_output=True,
        text=True,
    )
    assert stale.returncode == 1
    assert "evidence.sha256.mismatch" in stale.stderr
    assert "checkout/process.py:1-6" in stale.stderr
