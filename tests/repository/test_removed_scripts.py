from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REMOVED = (
    "skills/engineering/audit-codebase/scripts/apply_audit_classification.py",
    "skills/engineering/scope-issue/scripts/apply_issue_classification.py",
    "skills/engineering/scope-issue/scripts/scaffold_issue_plan.py",
    "skills/engineering/scope-issue/scripts/post_merge_issue_followup.py",
    "skills/engineering/implement-plan/scripts/record_change_diff.py",
    "skills/engineering/design-codebase/scripts/check_assessment.py",
    "skills/engineering/design-codebase/scripts/finalize_assessment.py",
)


def test_retired_runtime_scripts_stay_absent() -> None:
    assert all(not (ROOT / relative).exists() for relative in REMOVED)


def test_retired_runtime_scripts_are_not_documented() -> None:
    documented_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and ".agent" not in path.parts
        and ".scratch" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix.casefold() in {".md", ".json", ".yml", ".yaml", ".txt"}
    )
    assert all(Path(relative).name not in documented_text for relative in REMOVED)
