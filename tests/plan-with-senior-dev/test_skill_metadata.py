from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "plan-with-senior-dev"


def test_frontmatter_declares_existing_required_finalizer() -> None:
    content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(content.split("---", 2)[1])
    metadata = frontmatter["metadata"]
    assert metadata == {
        "plan-contract": "3",
        "finalizer": "scripts/finalize_plan.py",
        "validation-required": "true",
    }
    assert (SKILL / metadata["finalizer"]).is_file()
