from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "engineering" / "plan-change"
ACTIVE_MARKDOWN = (
    SKILL / "SKILL.md",
    SKILL / "references" / "cognitive-protocols.md",
    SKILL / "references" / "task-playbooks.md",
    SKILL / "references" / "adversarial-verification.md",
    SKILL / "references" / "worked-examples.md",
    SKILL / "references" / "plan-contract.md",
)


def test_active_workflow_docs_are_v4_and_utf8_clean() -> None:
    for path in ACTIVE_MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"plan-contract:\s*[123]", text, re.IGNORECASE), path
        assert not re.search(r"\bv[123]\s+(?:record|plan|contract)", text, re.IGNORECASE), path
        assert not any(marker in text for marker in ("â", "Ã", "�")), path


def test_skill_orders_the_v4_workflow_and_context_pointers() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    stages = (
        "## 1. Establish the planning boundary",
        "## 2. Ground and classify the change",
        "## 3. Scaffold the v4 plan and complete its records",
        "## 4. Attack the draft",
        "## 5. Finalize the exact draft",
    )
    positions = [text.index(stage) for stage in stages]
    assert positions == sorted(positions)
    for pointer in (
        "references/plan-contract.json",
        "references/cognitive-protocols.md",
        "references/task-playbooks.md",
        "references/worked-examples.md",
        "references/adversarial-verification.md",
        "scripts/snapshot_repository.py",
        "scripts/scaffold_plan.py",
        "scripts/finalize_plan.py",
    ):
        assert pointer in text
