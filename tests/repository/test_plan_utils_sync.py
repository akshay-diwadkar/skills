from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_SCRIPTS = REPO_ROOT / "plan-with-senior-dev" / "scripts"
IMPLEMENT_SCRIPTS = REPO_ROOT / "implement-with-senior-dev" / "scripts"


def test_shared_plan_utils_functions_are_synchronized() -> None:
    plan_utils_path = PLAN_SCRIPTS / "_plan_utils.py"
    implement_utils_path = IMPLEMENT_SCRIPTS / "_plan_utils.py"

    assert plan_utils_path.is_file(), f"Missing {plan_utils_path}"
    assert implement_utils_path.is_file(), f"Missing {implement_utils_path}"

    plan_text = plan_utils_path.read_text(encoding="utf-8")
    implement_text = implement_utils_path.read_text(encoding="utf-8")

    # Functions that MUST be synchronized byte-for-byte across both skills
    shared_functions = [
        "strip_fenced_code_blocks",
        "_normalized_lines",
        "receipt_lines",
        "canonical_plan_body",
        "plan_digest",
        "validate_receipt",
        "finalize_plan_text",
    ]

    for func in shared_functions:
        assert f"def {func}" in plan_text, f"{func} missing from plan-with-senior-dev _plan_utils.py"
        assert f"def {func}" in implement_text, f"{func} missing from implement-with-senior-dev _plan_utils.py"

    # Regex definitions that MUST match
    assert "VALIDATION_PREFIX_RE =" in plan_text
    assert "VALIDATION_PREFIX_RE =" in implement_text
    assert "VALIDATION_RECEIPT_RE =" in plan_text
    assert "VALIDATION_RECEIPT_RE =" in implement_text
