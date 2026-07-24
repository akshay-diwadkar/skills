import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "optimize-codebase-with-senior-dev"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase-with-senior-dev" / "scripts"
EXAMPLES = REPO_ROOT / "skills" / "engineering" / "optimize-codebase-with-senior-dev" / "references" / "worked-examples.md"
sys.path.insert(0, str(SCRIPTS))

from check_optimization import validate  # noqa: E402


def test_every_worked_example_validates_against_its_fixture() -> None:
    text = EXAMPLES.read_text(encoding="utf-8")
    matches = re.findall(
        r"<!-- example: (?P<case>[^ ]+) -->\s*```optimization\n(?P<report>.*?)\n```",
        text,
        re.DOTALL,
    )

    assert len(matches) == 4
    for case_id, report in matches:
        marker = re.search(
            r"<!-- optimization-contract: 1; scope: (?P<scope>targeted|sweep); stage: (?P<stage>plan|implementation) -->",
            report,
        )
        assert marker is not None, case_id
        fixture = DEV_DIR / "evals" / "fixtures" / case_id
        diagnostics = validate(report + "\n", marker.group("scope"), marker.group("stage"), fixture)
        assert diagnostics == [], (case_id, [item.to_dict() for item in diagnostics])
