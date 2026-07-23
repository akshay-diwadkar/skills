<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: 241752c366ab62e065663bfd4446d45c3400f8d16b03a21e5df97cc304ecb51a -->

# Reject division by zero

## Outcome
Division by zero raises `ValueError` with message `zero divisor`.

## Scope
Only `src/math_ops.py` and `tests/test_math_ops.py` change.

## Change
Guard the divisor before division.

## Verification
Run `python -m pytest -q` and expect all tests to pass.
