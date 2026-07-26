from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import finalized_text, validate_plan  # noqa: E402

SPEC = importlib.util.spec_from_file_location("plan_scaffold_contract", SCRIPTS / "plan_contract.py")
assert SPEC and SPEC.loader
SCAFFOLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAFFOLD)


def _hydrated(tmp_path: Path, tier: str, domains: list[str]) -> str:
    (tmp_path / "src").mkdir(exist_ok=True)
    source = "def target(raw: str) -> str:\n    return raw.strip()\n"
    path = tmp_path / "src" / "target.py"
    path.write_text(source, encoding="utf-8")
    excerpt = "def target(raw: str) -> str:\n"
    text = SCAFFOLD.render_scaffold(tier, "bug-fix", domains)
    replacements = {
        "REPLACE_CURRENT_PATH": "src/target.py",
        "REPLACE_CURRENT_RANGE": "1-1",
        "REPLACE_CURRENT_ANCHOR": "target",
        "REPLACE_CURRENT_HASH": hashlib.sha256(excerpt.encode()).hexdigest(),
        "REPLACE_CURRENT_FILE_HASH": hashlib.sha256(path.read_bytes()).hexdigest(),
        "REPLACE_EXACT_SIGNATURE": "raw: str",
        "REPLACE_EXACT_RETURN": "str",
        "REPLACE_TARGETED_TEST.py": "test_target.py",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    for domain in domains:
        text = text.replace(f"REPLACE_{domain}.py", f"test_{domain}.py")
    return text


@pytest.mark.parametrize(
    ("tier", "domains"),
    [
        ("tiny", []),
        ("standard", []),
        *[("high-risk", [domain]) for domain in sorted(SCAFFOLD.RISK_DOMAINS)],
        ("high-risk", ["public-contract", "durable-state"]),
        ("high-risk", ["security", "public-contract", "migration"]),
        ("high-risk", ["concurrency", "external-integration", "irreversible-external-effect"]),
    ],
)
def test_hydrated_scaffolds_validate_and_finalize(tmp_path: Path, tier: str, domains: list[str]) -> None:
    draft = _hydrated(tmp_path, tier, domains)
    _plan, diagnostics = validate_plan(draft, tmp_path)
    assert diagnostics == []
    finalized = finalized_text(draft, tmp_path)
    _plan, diagnostics = validate_plan(finalized, tmp_path, require_finalized=True)
    assert diagnostics == []


def test_high_risk_scaffold_requires_a_domain() -> None:
    with pytest.raises(ValueError, match="at least one risk domain"):
        SCAFFOLD.render_scaffold("high-risk", "feature", [])
