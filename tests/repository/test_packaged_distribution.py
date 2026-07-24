from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "packaging"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import build_distribution  # noqa: E402
import validate_repository  # noqa: E402
import verify_distribution  # noqa: E402


def test_build_and_verify_clean_distribution() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)
        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert not errors, "Distribution verification failed:\n" + "\n".join(errors)

        # 1. Verify Codex installer exists
        installer = dist_path / "tools" / "agents" / "install_codex_agents.py"
        assert installer.is_file(), "Codex installer missing in built distribution"

        # 2. Verify docs exist
        assert (dist_path / "docs" / "installation.md").is_file()
        assert (dist_path / "docs" / "compatibility.md").is_file()

        # 3. Verify no dev artifacts exist
        forbidden_names = {"browser_smoke.py", "conftest.py", "debug_hash.py"}
        for p in dist_path.rglob("*"):
            assert p.name not in forbidden_names, f"Forbidden file in dist: {p}"
            assert not p.name.startswith("test_"), f"Test file in dist: {p}"
            assert "tests" not in p.parts, f"Tests dir in dist: {p}"
            assert "evals" not in p.parts, f"Evals dir in dist: {p}"
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_release_readme_transformation(tmp_path: Path) -> None:
    """Verify build_release_readme removes maintainer sections and converts maintainer doc links to absolute GitHub links."""
    src_readme = tmp_path / "README_src.md"
    out_readme = tmp_path / "README_out.md"

    src_content = (
        "# Title\n\n"
        "Overview text.\n\n"
        "[User Doc](docs/installation.md)\n"
        "[Maintainer Doc](docs/testing.md)\n"
        "[Maintainer Root](CONTRIBUTING.md)\n\n"
        "## Maintainer Verification (Source Repository)\n\n"
        "Maintainer text and commands.\n\n"
        "## Contributing, Security & License\n\n"
        "Footer text.\n"
    )
    src_readme.write_text(src_content, encoding="utf-8")

    build_distribution.build_release_readme(src_readme, out_readme)

    assert out_readme.is_file()
    text = out_readme.read_text(encoding="utf-8")

    assert "## Maintainer Verification" not in text
    assert "Maintainer text and commands." not in text
    assert "[User Doc](docs/installation.md)" in text
    assert "[Maintainer Doc](https://github.com/akshay-diwadkar/skills/blob/main/docs/testing.md)" in text
    assert "[Maintainer Root](https://github.com/akshay-diwadkar/skills/blob/main/CONTRIBUTING.md)" in text
    assert "## Contributing, Security & License" in text


def test_verify_distribution_rejects_missing_command_target() -> None:
    """Verify distribution validator rejects Markdown files referencing non-existent script targets."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-err-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)

        # Inject invalid command reference into a bundled doc
        doc_file = dist_path / "docs" / "getting-started.md"
        assert doc_file.is_file()
        current_text = doc_file.read_text(encoding="utf-8")
        doc_file.write_text(current_text + "\nRun `python tools/nonexistent_script.py`\n", encoding="utf-8")

        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert any("references missing command target file: tools/nonexistent_script.py" in err for err in errors), (
            f"Expected verification error for missing command target, got: {errors}"
        )
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_verify_distribution_rejects_source_only_relative_link() -> None:
    """Verify relative link to a file present only in source repository is rejected during bundle verification."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-link-err-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)

        doc_file = dist_path / "docs" / "getting-started.md"
        assert doc_file.is_file()
        current_text = doc_file.read_text(encoding="utf-8")
        # docs/testing.md is excluded from bundle, but exists in source repo
        doc_file.write_text(current_text + "\n[Testing Strategy](testing.md)\n", encoding="utf-8")

        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert any("broken relative link target 'testing.md'" in err for err in errors), (
            f"Expected error for missing bundle relative link, got: {errors}"
        )
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_verify_distribution_allows_absolute_github_links() -> None:
    """Verify absolute GitHub URLs to maintainer docs are allowed in distribution bundle."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-abs-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)

        doc_file = dist_path / "docs" / "getting-started.md"
        current_text = doc_file.read_text(encoding="utf-8")
        doc_file.write_text(
            current_text + "\n[Testing](https://github.com/akshay-diwadkar/skills/blob/main/docs/testing.md)\n",
            encoding="utf-8",
        )

        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert not any("testing.md" in err for err in errors), f"Absolute GitHub link generated error: {errors}"
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_verify_distribution_rejects_path_traversal() -> None:
    """Verify path traversal link pointing outside distribution root is rejected."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-traversal-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)

        doc_file = dist_path / "docs" / "getting-started.md"
        current_text = doc_file.read_text(encoding="utf-8")
        doc_file.write_text(current_text + "\n[Traverse](../../../docs/testing.md)\n", encoding="utf-8")

        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert any("path traversal outside distribution root" in err for err in errors), (
            f"Expected path traversal error, got: {errors}"
        )
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_per_skill_script_allowlist_validation() -> None:
    """Verify per-skill script mapping allows valid scripts for their owning skill and rejects misplaced or unknown scripts."""
    catalog = {
        "skills": [
            {"name": "create-diagram", "path": "skills/engineering/create-diagram"},
            {"name": "plan-with-senior-dev", "path": "skills/engineering/plan-with-senior-dev"},
        ]
    }

    # 1. Shipped scripts pass
    tracked_valid = [
        "skills/engineering/create-diagram/SKILL.md",
        "skills/engineering/create-diagram/scripts/build_diagram.py",
        "skills/engineering/plan-with-senior-dev/SKILL.md",
        "skills/engineering/plan-with-senior-dev/scripts/scaffold_plan.py",
    ]
    errs_valid = validate_repository.validate_package_boundaries(tracked_valid, catalog)
    assert not errs_valid, f"Expected no errors for valid tracked files, got: {errs_valid}"

    # 2. Script allowed for plan-with-senior-dev placed under create-diagram is rejected
    tracked_misplaced = [
        "skills/engineering/create-diagram/scripts/scaffold_plan.py",
    ]
    errs_misplaced = validate_repository.validate_package_boundaries(tracked_misplaced, catalog)
    assert any("Unrecognized runtime script inside skill package 'create-diagram'" in err for err in errs_misplaced), (
        f"Expected error for misplaced script, got: {errs_misplaced}"
    )

    # 3. Unknown script is rejected
    tracked_unknown = [
        "skills/engineering/create-diagram/scripts/unknown_script.py",
    ]
    errs_unknown = validate_repository.validate_package_boundaries(tracked_unknown, catalog)
    assert any("Unrecognized runtime script inside skill package 'create-diagram'" in err for err in errs_unknown), (
        f"Expected error for unknown script, got: {errs_unknown}"
    )
