import subprocess
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from link_agent_docs import MANAGED_BEGIN, MANAGED_END, AgentDocumentError, ensure_agent_docs


def _block_count(content: str) -> int:
    return content.count(MANAGED_BEGIN) + content.count(MANAGED_END)


def _assert_navigation_workflow(content: str, knowledge_path: str) -> None:
    assert knowledge_path in content
    for instruction in (
        "Before broad exploration, check freshness.",
        "Build or refresh only when knowledge is missing, invalid, or stale.",
        "Resolve the current task at phase 1; read only its returned targets and selected symbol shards.",
        "Expand to later phases only when phase 1's stop condition is unmet.",
        "Verify conclusions in current source, then refresh after a coherent change set.",
        "Do not preload all maps or shards. Knowledge guides navigation; source remains authoritative.",
    ):
        assert instruction in content


def test_neither_file_exists_creates_both_with_default_path(tmp_path: Path):
    result = ensure_agent_docs(tmp_path)

    assert result["created"] == ["AGENTS.md", "CLAUDE.md"]
    for name in ("AGENTS.md", "CLAUDE.md"):
        content = (tmp_path / name).read_text(encoding="utf-8")
        assert content.startswith(f"# {name}\n\n")
        assert _block_count(content) == 2
        _assert_navigation_workflow(content, ".agent/knowledge/")


def test_only_agents_exists_preserves_user_content_and_creates_claude(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project Instructions\n\nUse Python 3.12.\n", encoding="utf-8")

    result = ensure_agent_docs(tmp_path)

    assert result["modified"] == ["AGENTS.md"]
    assert result["created"] == ["CLAUDE.md"]
    assert "Use Python 3.12." in agents.read_text(encoding="utf-8")
    assert _block_count(agents.read_text(encoding="utf-8")) == 2


def test_only_claude_exists_preserves_user_content_and_creates_agents(tmp_path: Path):
    claude = tmp_path / "CLAUDE.md"
    claude.write_text("# Claude Rules\n\nKeep this footer.\n", encoding="utf-8")

    result = ensure_agent_docs(tmp_path)

    assert result["created"] == ["AGENTS.md"]
    assert result["modified"] == ["CLAUDE.md"]
    assert "Keep this footer." in claude.read_text(encoding="utf-8")


def test_existing_blocks_are_updated_in_place_and_idempotent(tmp_path: Path):
    for name in ("AGENTS.md", "CLAUDE.md"):
        (tmp_path / name).write_text(
            f"# Header\n\n{MANAGED_BEGIN}\nold generated content\n{MANAGED_END}\n\n## Footer\nKeep me.\n",
            encoding="utf-8",
        )

    first = ensure_agent_docs(tmp_path)
    before = {name: (tmp_path / name).read_bytes() for name in ("AGENTS.md", "CLAUDE.md")}
    second = ensure_agent_docs(tmp_path)

    assert first["modified"] == ["AGENTS.md", "CLAUDE.md"]
    assert second["unchanged"] == ["AGENTS.md", "CLAUDE.md"]
    assert before == {name: (tmp_path / name).read_bytes() for name in before}
    assert all("Keep me." in (tmp_path / name).read_text(encoding="utf-8") for name in before)


def test_custom_output_path_is_reflected_in_both_files(tmp_path: Path):
    result = ensure_agent_docs(tmp_path, ".cache/custom-map")

    assert result["knowledge_path"] == ".cache/custom-map"
    for name in ("AGENTS.md", "CLAUDE.md"):
        content = (tmp_path / name).read_text(encoding="utf-8")
        _assert_navigation_workflow(content, ".cache/custom-map/")
        assert ".agent/knowledge/" not in content


def test_opt_out_is_per_file(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    original = "<!-- OPT-OUT MAP-CODEBASE -->\n# Custom Rules\n"
    agents.write_text(original, encoding="utf-8")

    result = ensure_agent_docs(tmp_path)

    assert result["skipped"] == ["AGENTS.md"]
    assert result["created"] == ["CLAUDE.md"]
    assert agents.read_text(encoding="utf-8") == original


def test_both_opted_out_are_unchanged(tmp_path: Path):
    for name in ("AGENTS.md", "CLAUDE.md"):
        (tmp_path / name).write_text("<!-- OPT-OUT MAP-CODEBASE -->\n", encoding="utf-8")

    result = ensure_agent_docs(tmp_path)

    assert result["skipped"] == ["AGENTS.md", "CLAUDE.md"]
    assert result["created"] == []
    assert result["modified"] == []


@pytest.mark.parametrize(
    "filename, content",
    [
        ("AGENTS.md", f"{MANAGED_BEGIN}\n"),
        ("CLAUDE.md", f"{MANAGED_END}\n"),
        ("AGENTS.md", f"{MANAGED_BEGIN}\nx\n{MANAGED_END}\n{MANAGED_BEGIN}\ny\n{MANAGED_END}\n"),
        ("CLAUDE.md", f"{MANAGED_END}\nx\n{MANAGED_BEGIN}\n"),
    ],
)
def test_malformed_blocks_reject_without_partial_writes(tmp_path: Path, filename: str, content: str):
    target = tmp_path / filename
    other = tmp_path / ("CLAUDE.md" if filename == "AGENTS.md" else "AGENTS.md")
    target.write_text(content, encoding="utf-8")
    other.write_text("# Existing\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in (target, other)}

    with pytest.raises(AgentDocumentError, match=filename):
        ensure_agent_docs(tmp_path)

    assert before == {path: path.read_bytes() for path in before}


def test_link_docs_cli_creates_both_missing_files(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "cli.py"), "link-docs", "--repo-root", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()


def _run_cli(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "cli.py"), *args, "--repo-root", str(repo_root), "--format", "json"],
        capture_output=True,
        text=True,
    )


def test_build_cli_finalizes_existing_docs_and_uses_custom_output(sample_repo: Path):
    agents = sample_repo / "AGENTS.md"
    claude = sample_repo / "CLAUDE.md"
    agents.write_text("# Project Rules\n", encoding="utf-8")
    claude.write_text("# Claude Rules\n", encoding="utf-8")

    result = _run_cli(sample_repo, "build", "--output", ".cache/custom-map")

    assert result.returncode == 0, result.stderr
    assert '"agent_docs"' in result.stdout
    for path in (agents, claude):
        content = path.read_text(encoding="utf-8")
        assert ".cache/custom-map/" in content
        assert _block_count(content) == 2
    assert (sample_repo / ".cache" / "custom-map" / "manifest.json").is_file()


def test_refresh_cli_recreates_missing_instruction_file(sample_repo: Path):
    assert _run_cli(sample_repo, "build").returncode == 0
    (sample_repo / "CLAUDE.md").unlink()

    result = _run_cli(sample_repo, "refresh")

    assert result.returncode == 0, result.stderr
    assert (sample_repo / "CLAUDE.md").is_file()
    assert _block_count((sample_repo / "AGENTS.md").read_text(encoding="utf-8")) == 2


def test_metadata_only_refresh_finalizes_missing_instruction_file(sample_repo: Path):
    assert _run_cli(sample_repo, "build").returncode == 0
    subprocess.run(["git", "commit", "--allow-empty", "-m", "metadata only"], cwd=sample_repo, check=True)
    (sample_repo / "CLAUDE.md").unlink()

    result = _run_cli(sample_repo, "refresh")

    assert result.returncode == 0, result.stderr
    assert '"mode": "metadata-only"' in result.stdout
    assert (sample_repo / "CLAUDE.md").is_file()


def test_build_cli_reports_finalization_failure_without_traceback_or_partial_writes(sample_repo: Path):
    agents = sample_repo / "AGENTS.md"
    claude = sample_repo / "CLAUDE.md"
    agents.write_text(f"{MANAGED_BEGIN}\n", encoding="utf-8")
    claude.write_text("# Keep untouched\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in (agents, claude)}

    result = _run_cli(sample_repo, "build")

    assert result.returncode != 0
    assert "Knowledge artifacts were created, but agent-document finalization failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert before == {path: path.read_bytes() for path in before}
    assert (sample_repo / ".agent" / "knowledge" / "manifest.json").is_file()
