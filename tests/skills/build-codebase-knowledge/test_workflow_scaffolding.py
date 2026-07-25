import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from scaffold_github_workflow import scaffold_github_workflow


def test_scaffold_modes_and_pinned_shas(tmp_path: Path):
    res_cli = scaffold_github_workflow(tmp_path, branch="main", mode="cli", force=True)
    assert res_cli["status"] == "success"

    wf_file = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    content = wf_file.read_text(encoding="utf-8")

    assert "uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11" in content
    assert "paths-ignore: ['.agent/knowledge/**', 'AGENTS.md', 'CLAUDE.md']" in content
    assert "repository: akshay-diwadkar/skills" in content
    assert "ref: 09a44216123f4621a59ef965ccaa5aa96d3a2e5a" in content
    assert ".codebase-knowledge-runtime/skills/engineering/build-codebase-knowledge/scripts/cli.py" in content
    assert "pip install build-codebase-knowledge" not in content
    assert "[skip ci]" in content

    # Test vendored mode
    res_vendored = scaffold_github_workflow(tmp_path, branch="main", mode="vendored", force=True)
    assert res_vendored["status"] == "success"
    content_vendored = wf_file.read_text(encoding="utf-8")
    assert "repository: akshay-diwadkar/skills" in content_vendored
