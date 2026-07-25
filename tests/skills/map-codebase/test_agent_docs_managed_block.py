import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from link_agent_docs import MANAGED_BEGIN, MANAGED_END, link_agent_docs


def test_managed_block_creation_and_update(tmp_path: Path):
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("# User Written Agent Rules\n- Rule 1: Always verify.\n", encoding="utf-8")

    res1 = link_agent_docs(tmp_path)
    assert "AGENTS.md" in res1["modified"]

    content1 = agents_file.read_text(encoding="utf-8")
    assert "# User Written Agent Rules" in content1
    assert MANAGED_BEGIN in content1
    assert MANAGED_END in content1

    # Second run: idempotency test
    res2 = link_agent_docs(tmp_path)
    assert len(res2["modified"]) == 0
    assert agents_file.read_text(encoding="utf-8") == content1


def test_managed_block_opt_out(tmp_path: Path):
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("<!-- OPT-OUT BUILD-CODEBASE-KNOWLEDGE -->\n# Custom Rules\n", encoding="utf-8")

    res = link_agent_docs(tmp_path)
    assert len(res["modified"]) == 0
    assert MANAGED_BEGIN not in agents_file.read_text(encoding="utf-8")
