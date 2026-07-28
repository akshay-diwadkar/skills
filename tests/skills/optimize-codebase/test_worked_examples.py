import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "optimize-codebase"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "scripts"
EXAMPLES = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "references" / "worked-examples.md"
sys.path.insert(0, str(SCRIPTS))

from check_optimization import validate  # noqa: E402


def test_every_worked_example_validates_against_its_fixture() -> None:
    text = EXAMPLES.read_text(encoding="utf-8")
    reports = re.findall(
        r"<!-- example: (?P<case>[^ ]+) -->\s*```optimization\n(?P<report>.*?)\n```",
        text,
        re.DOTALL,
    )
    handoffs = {
        case: handoff
        for case, handoff in re.findall(
            r"<!-- handoff: (?P<case>[^ ]+) -->\s*```request\n(?P<handoff>.*?)\n```",
            text,
            re.DOTALL,
        )
    }

    assert len(reports) == 2
    for case_id, report in reports:
        marker = re.search(
            r"<!-- optimization-contract: 2; path: (?P<path>fast|full); scope: (?P<scope>targeted|sweep); stage: (?P<stage>plan|implementation) -->",
            report,
        )
        assert marker is not None, case_id
        fixture = DEV_DIR / "worked-example-fixtures" / case_id
        diagnostics = validate(
            report + "\n",
            marker.group("path"),
            marker.group("scope"),
            marker.group("stage"),
            fixture,
            handoffs.get(case_id),
        )
        assert diagnostics == [], (case_id, [item.to_dict() for item in diagnostics])
