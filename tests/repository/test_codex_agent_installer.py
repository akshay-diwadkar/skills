from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "agents"))

import install_codex_agents  # noqa: E402


def test_codex_installer_dry_run_and_write_mode() -> None:
    with tempfile.TemporaryDirectory(prefix="test-codex-target-") as tmpdir:
        target = Path(tmpdir)

        # 1. Dry run test
        actions, errors = install_codex_agents.install_codex_agents(target, write=False, force=False)
        assert errors == []
        assert len(actions) == 5  # 4 agents + 1 config
        assert not (target / ".codex").exists()

        # 2. Write mode test
        actions_write, errors_write = install_codex_agents.install_codex_agents(target, write=True, force=False)
        assert errors_write == []
        assert (target / ".codex" / "agents" / "architecture-engineer.toml").is_file()
        assert (target / ".codex" / "config.toml").is_file()

        # 3. Re-run without force (identical files should skip)
        actions_rerun, errors_rerun = install_codex_agents.install_codex_agents(target, write=False, force=False)
        assert errors_rerun == []
        assert all("SKIP" in act for act in actions_rerun)

        # 4. Modify destination file and test refusal without --force
        dest_file = target / ".codex" / "agents" / "architecture-engineer.toml"
        dest_file.write_text("# modified content", encoding="utf-8")

        _, errors_modified = install_codex_agents.install_codex_agents(target, write=False, force=False)
        assert len(errors_modified) == 1
        assert "Use --force" in errors_modified[0]

        # 5. Overwrite with --force
        actions_force, errors_force = install_codex_agents.install_codex_agents(target, write=True, force=True)
        assert errors_force == []
        assert any("REPLACE" in act for act in actions_force)
