import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from resolve_task import _signals, classify_task_intent

CASES = [
    ("d07f1a38b387b02109daa5a810dd96943c7060a7", "Stabilize tiny fixture line endings", "test"),
    ("eb87c76e38a5b95f639eb470e665caf8ef9dfd34", "Improve plan-change v5 guidance", "source"),
    ("774cc6ff6143c6050a4c703288c30140a84c5704", "Harden plan-change v5 release gates", "source"),
    ("e562078efcd44e3c7714eb7f1d6a776da682dec0", "Harden plan-change v5 contracts", "source"),
    ("bf7b0a3ff33c342e99b37ba800b4123f8908edc7", "Fix plan-change CLI type checks", "source"),
    ("c923bcd2292cc5617a02a5871ca9b604c8bc21c3", "Fix plan-change lint ordering", "source"),
    ("402a91e05fb52e964ac63a2b2b32208b0cf56c25", "Rebuild v5 high-risk scaffolds", "source"),
    ("a52b8ffce95c845dd6667cf955ff0fb8dc492763", "Strengthen cited Python fact verification", "source"),
    ("0a8d30967aa87f7461e7c8605e82e3ce31872656", "ci: add GitHub Release workflow with automated tagging and release assets", "configuration"),
    ("b8da01a03390979dcf39548fabd8be173ff6b6df", "fix(ci): update stale test paths in quality workflow and documentation", "configuration"),
    ("fixture-composition", "Find the collector composition root and OTLP configuration", "source"),
    ("fixture-impact", "If collector orchestration changes, identify the pipeline and its behavior test", "source"),
    ("fixture-registry", "If component registration changes, locate the registry and direct test", "source"),
]


@pytest.mark.parametrize(("_commit", "title", "expected_role"), CASES)
def test_real_commit_title_conventions_use_scored_rules(
    _commit: str, title: str, expected_role: str
) -> None:
    intent = classify_task_intent(title, _signals(title), [])
    assert intent.primary_role == expected_role


def test_strong_symbol_keeps_requested_configuration_and_test_roles() -> None:
    files = [{"path": "go/pipeline/pipeline.go", "role": "source", "symbols": ["CollectOTLP"]}]
    intent = classify_task_intent(
        "Find CollectOTLP and its receiver configuration and behavior test.",
        _signals("Find CollectOTLP and its receiver configuration and behavior test."),
        files,
    )
    assert intent.primary_role == "source"
    assert intent.secondary_roles == ("configuration", "test")
