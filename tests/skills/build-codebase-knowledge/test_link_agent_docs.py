import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from link_agent_docs import link_agent_docs


def test_link_agent_docs_both_exist(tmp_path: Path):
    agents_file = tmp_path / "AGENTS.md"
    claude_file = tmp_path / "CLAUDE.md"
    agents_file.write_text("# Existing Agents Guide\n", encoding="utf-8")
    claude_file.write_text("# Existing Claude Guide\n", encoding="utf-8")

    res = link_agent_docs(tmp_path)
    assert res["status"] == "success"
    assert "AGENTS.md" in res["modified"]
    assert "CLAUDE.md" in res["modified"]
    assert len(res["created"]) == 0

    content_agents = agents_file.read_text(encoding="utf-8")
    content_claude = claude_file.read_text(encoding="utf-8")
    assert ".agent/knowledge/" in content_agents
    assert ".agent/knowledge/" in content_claude

    # Idempotency test: calling again should not duplicate
    res_again = link_agent_docs(tmp_path)
    assert len(res_again["modified"]) == 0
    assert len(res_again["created"]) == 0
    assert agents_file.read_text(encoding="utf-8") == content_agents


def test_link_agent_docs_only_agents_exists(tmp_path: Path):
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("# Only Agents File\n", encoding="utf-8")

    res = link_agent_docs(tmp_path)
    assert res["status"] == "success"
    assert "AGENTS.md" in res["modified"]
    assert res["created"] == []
    assert not (tmp_path / "CLAUDE.md").exists()


def test_link_agent_docs_only_claude_exists(tmp_path: Path):
    claude_file = tmp_path / "CLAUDE.md"
    claude_file.write_text("# Only Claude File\n", encoding="utf-8")

    res = link_agent_docs(tmp_path)
    assert res["status"] == "success"
    assert "CLAUDE.md" in res["modified"]
    assert res["created"] == []
    assert not (tmp_path / "AGENTS.md").exists()


def test_link_agent_docs_neither_exists(tmp_path: Path):
    res = link_agent_docs(tmp_path)
    assert res["status"] == "success"
    assert res["created"] == []
    res = link_agent_docs(tmp_path, create_missing=True)
    assert res["created"] == ["AGENTS.md"]
    assert not (tmp_path / "CLAUDE.md").exists()

    agents_file = tmp_path / "AGENTS.md"
    claude_file = tmp_path / "CLAUDE.md"
    assert agents_file.is_file()
    assert not claude_file.exists()

    agents_content = agents_file.read_text(encoding="utf-8")
    assert "check freshness" in agents_content
    assert "phase 1" in agents_content
