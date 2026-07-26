from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import validate_plan  # noqa: E402

SPEC = importlib.util.spec_from_file_location("hardening_helpers", Path(__file__).with_name("hardening_helpers.py"))
assert SPEC and SPEC.loader
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _signals(text: str, signals: list[str]) -> str:
    match = re.search(r"<!-- plan-metadata: (.+) -->", text)
    assert match
    metadata = json.loads(match.group(1))
    metadata["provisional"]["tier_signals"] = signals
    metadata["final"]["tier_signals"] = signals
    return text[: match.start(1)] + json.dumps(metadata, separators=(",", ":")) + text[match.end(1) :]


@pytest.mark.parametrize(
    "signal",
    [
        "transitive-consumers",
        "shared-internal-interface",
        "uncertain-root-cause",
        "multiple-architectural-layers",
        "mixed-sync-async-consumers",
        "multiple-test-surfaces",
    ],
)
def test_every_typed_signal_escalates_tiny_to_standard(tmp_path: Path, signal: str) -> None:
    text = _signals(HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", []), [signal])
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "tier.minimum" and "standard" in item.message for item in diagnostics)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("locality", "shared-production"),
        ("locality", "test-only"),
        ("reversibility", "conditional"),
        ("reversibility", "irreversible"),
        ("status", "new"),
    ],
)
def test_tiny_requires_one_existing_local_reversible_production_change(
    tmp_path: Path, field: str, value: str
) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text = text.replace(
        f"{field}: {next(part.split(': ', 1)[1] for part in next(line for line in text.splitlines() if line.startswith('- CH-1:')).split(' | ') if part.startswith(field + ': '))}",
        f"{field}: {value}",
    )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "tier.minimum" for item in diagnostics)


def test_transitive_consumer_record_escalates_even_when_signal_is_omitted(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text = text.replace("surface: direct-caller", "surface: transitive-consumer")
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "tier.minimum" for item in diagnostics)
