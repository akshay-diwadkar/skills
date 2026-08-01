from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCES = (
    REPO_ROOT
    / "skills"
    / "engineering"
    / "optimize-codebase"
    / "references"
)


def test_consolidated_references_replace_absorbed_portfolio() -> None:
    assert {path.name for path in REFERENCES.iterdir()} == {
        "fast-path.md",
        "optimization-contract.json",
        "handoff-contract.json",
        "optimization-contract.md",
        "optimization-techniques.md",
    }

    fast_path = (REFERENCES / "fast-path.md").read_text(encoding="utf-8")
    merged = "\n".join(
        (REFERENCES / name).read_text(encoding="utf-8")
        for name in ("optimization-contract.md", "optimization-techniques.md")
    )
    assert "only when every criterion is already proved" in fast_path
    assert "Revert the introduced patch if behavior regresses" in fast_path
    for required in ("baseline", "rollback", "ecosystem", "pattern"):
        assert required in merged
