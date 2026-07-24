from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "packaging"))

import build_distribution  # noqa: E402
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
