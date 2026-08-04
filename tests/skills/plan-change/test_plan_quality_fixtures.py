"""Offline plan-quality fixture suite runner (CH-21/CH-22/CH-23).

Every golden plan in fixtures/v7-quality must seal and score complete; every
weak plan must fail for its intended reason, either at sealing (reject mode)
or at scoring (score mode). The suite runs the local v7 runtime and the
deterministic scorer only: no provider, model, agent harness, or network call.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / "v7-quality"

sys.path.insert(0, str(ROOT / "tests" / "skills" / "plan-change"))
import v6_helpers as HELPERS  # noqa: E402

sys.path.insert(0, str(ROOT / "tests" / "skills" / "plan-change" / "evals" / "tools"))
import score_plan_quality as SCORER  # noqa: E402

RUNTIME = HELPERS.RUNTIME

SCENARIOS = [path for path in sorted(FIXTURES.iterdir()) if (path / "manifest.json").is_file()]


def _typed_handoff(kind: str, body: str) -> bytes:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"<!-- {kind}-handoff: 1; sha256: {digest} -->\n{body}".encode("utf-8")


def _manifest(scenario: Path) -> dict:
    return json.loads((scenario / "manifest.json").read_text(encoding="utf-8"))


def _request_file(scenario: Path, manifest: dict, tmp_path: Path) -> Path:
    kind = manifest.get("handoff_kind")
    if kind:
        request = tmp_path / "request.md"
        body = (scenario / "handoff-body.md").read_text(encoding="utf-8")
        request.write_bytes(_typed_handoff(kind, body))
        return request
    return scenario / "request.md"


def _repo(scenario: Path, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(scenario / "repo", repo)
    return repo


def _seal(scenario: Path, manifest: dict, tmp_path: Path, draft: Path) -> tuple[Path, Path, object]:
    repo = _repo(scenario, tmp_path)
    request = _request_file(scenario, manifest, tmp_path)
    sealed = RUNTIME.seal_plan(repo, request, draft, handoff_item=manifest.get("handoff_item"))
    return repo, request, sealed


@pytest.mark.parametrize("name", [path.name for path in SCENARIOS])
def test_golden_plan_seals_and_scores_complete(name: str, tmp_path: Path) -> None:
    scenario = FIXTURES / name
    manifest = _manifest(scenario)
    repo, request, sealed = _seal(scenario, manifest, tmp_path, scenario / "golden.md")
    plan, diagnostics, _ = RUNTIME.verify_sealed_plan(sealed.text, repo, request_bytes=request.read_bytes())
    assert diagnostics == []
    assert plan is not None
    report = SCORER.score_plan(plan, manifest)
    assert report["missing"] == [], report


WEAK_CASES = [
    (scenario.name, weak_name)
    for scenario in SCENARIOS
    for weak_name in sorted(_manifest(scenario).get("weak", {}))
]


@pytest.mark.parametrize(("scenario", "weak_name"), WEAK_CASES)
def test_weak_plan_fails_for_intended_reason(scenario: str, weak_name: str, tmp_path: Path) -> None:
    sdir = FIXTURES / scenario
    manifest = _manifest(sdir)
    spec = manifest["weak"][weak_name]
    draft = sdir / "weak" / f"{weak_name}.md"
    if spec["mode"] == "reject":
        with pytest.raises(ValueError) as excinfo:
            _seal(sdir, manifest, tmp_path, draft)
        codes = {diagnostic.code for diagnostic in getattr(excinfo.value, "diagnostics", [])}
        assert set(spec["expected_code"]) <= codes, codes
        return
    repo, request, sealed = _seal(sdir, manifest, tmp_path, draft)
    plan, diagnostics, _ = RUNTIME.verify_sealed_plan(sealed.text, repo, request_bytes=request.read_bytes())
    assert diagnostics == [], (weak_name, diagnostics)
    assert plan is not None
    report = SCORER.score_plan(plan, manifest)
    assert set(report["missing"]) == set(spec["expected_missing"]), (weak_name, report)


def test_scenario_manifest_schema_is_consistent() -> None:
    for scenario in SCENARIOS:
        manifest = _manifest(scenario)
        assert manifest["scenario"] == scenario.name
        assert manifest["request"] in {"request.md", "handoff-body.md"}
        assert bool(manifest.get("handoff_kind")) == (manifest["request"] == "handoff-body.md")
        assert (scenario / "golden.md").is_file()
        assert (scenario / manifest["request"]).is_file()
        assert (scenario / "repo").is_dir()
        for weak_name, spec in manifest["weak"].items():
            assert (scenario / "weak" / f"{weak_name}.md").is_file()
            assert spec["mode"] in {"score", "reject"}
            if spec["mode"] == "score":
                assert spec["expected_missing"]
            else:
                assert spec["expected_code"]


def test_fixture_suite_is_provider_free() -> None:
    assert len(SCENARIOS) == 12
    for scenario in SCENARIOS:
        manifest = _manifest(scenario)
        assert not {"provider", "model", "harness", "endpoint", "api_key"} & set(manifest)
        assert not set(scenario.rglob("*.exe")) and not set(scenario.rglob("*.sh"))
    assert "score_plan_quality" in str(SCORER.__file__)
    assert "plan_runtime" in str(RUNTIME.__file__)
