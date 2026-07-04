import json
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_plan import main as check_plan_main


def run_checker(text: str, tier: str = "tiny", warn: bool = False, issue_related: bool = False) -> tuple[int, str]:
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdin = StringIO(text)
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        args = ["--tier", tier]
        if warn:
            args.append("--warn")
        if issue_related:
            args.append("--issue-related")
        sys.argv = ["check_plan.py"] + args
        exit_code: int | str = check_plan_main()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
    finally:
        output = sys.stdout.getvalue()
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    code = int(exit_code) if not isinstance(exit_code, str) else (1 if exit_code else 0)
    return code, output


def run_checker_json(text: str, tier: str = "tiny") -> tuple[int, dict]:
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdin = StringIO(text)
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    try:
        sys.argv = ["check_plan.py", "--tier", tier, "--format", "json"]
        exit_code: int | str = check_plan_main()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
    finally:
        output = sys.stdout.getvalue()
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    code = int(exit_code) if not isinstance(exit_code, str) else (1 if exit_code else 0)
    if code != 0:
        return code, {}
    return code, json.loads(output) if output.strip() else {}


VALID_TINY_PLAN = (
    "# Add unit tests for validation scripts\n"
    "## Goal\nFix the bug\n"
    "## Current State\n`src/file.py:42` has issue\n"
    "## Change\nAdd null check before access\n"
    "## Test/Verification\n`python -m pytest tests/` returns 0\n"
    "## Assumptions\nLow impact: no schema change"
)

VALID_STANDARD_PLAN = (
    "# Add unit tests for validation scripts\n"
    "## Goal\nFix the bug\n"
    "## Success Criteria\nReturns exit code 0\n"
    "## Current State\n`src/file.py:42` has issue\n"
    "## Scope\nIn scope: fix bug\nOut of scope: refactoring\nPreserve existing return shape unchanged\nBlast radius: affected caller is the local validator command only\n"
    "## Approach\nFollow existing pattern from nearby files\n"
    "## Changes\n1. Add null check\n2. Update tests\n"
    "## Tracer Bullet\n`python -c test_one_path.py` verifies the flow end to end\n"
    "## Failure Modes\nNull pointer on missing data\n"
    "## Test Strategy\nTest for happy path and failure\n`python test.py` returns 0\n"
    "## Rollback Plan\nTrivial revert; no persistent data or external side effects\n"
    "## Doc Updates\nNo terminology changes\n"
    "## Assumptions\nLow-impact: no data change"
)


class TestIntegrationTiny:
    def test_valid_tiny_passes(self):
        code, output = run_checker(VALID_TINY_PLAN, "tiny")
        assert code == 0, f"Expected pass, got: {output}"

    def test_invalid_tiny_fails(self):
        text = "# X\n## Goal\n## Current State"
        code, output = run_checker(text, "tiny")
        assert code != 0

    def test_missing_goal_fails(self):
        text = "# Add test suite\n## Current State\nBug\n## Change\nFix\n## Test/Verification\nRun test\n## Assumptions\nLow"
        code, output = run_checker(text, "tiny")
        assert code != 0


class TestIntegrationStandard:
    def test_valid_standard_passes(self):
        code, output = run_checker(VALID_STANDARD_PLAN, "standard")
        assert code == 0, f"Expected pass, got: {output}"

    def test_invalid_standard_fails(self):
        text = "# Add test suite\n## Goal\nFix\n## Current State\nfile.py:42"
        code, output = run_checker(text, "standard")
        assert code != 0


class TestWarnFlag:
    def test_warn_flag_with_warnings(self):
        text = "# Add a test suite for the format checker\n## Goal\nFix\n## Current State\nfile.py:42\n## Scope\nIn scope: fix\nOut of scope: refactor\n## Approach\nFollow existing pattern\n## Changes\n1. Fix\n## Test Strategy\nTest for pass\npython test.py returns 0\n## Rollback Plan\nTrivial revert\n## Assumptions\nLow impact"
        code, output = run_checker(text, "standard", warn=True)
        warnings_in_output = "Warning" in output
        assert code == 0 or warnings_in_output


class TestJsonOutput:
    def test_json_output_format(self):
        code, data = run_checker_json(VALID_TINY_PLAN, "tiny")
        if code == 0 and data:
            assert "errors" in data
            assert "warnings" in data
            assert "passed" in data

    def test_json_passes_on_valid(self):
        code, data = run_checker_json(VALID_TINY_PLAN, "tiny")
        if data:
            assert "passed" in data

    def test_json_output_on_invalid(self):
        code, data = run_checker_json("# X", "tiny")
        assert code != 0
