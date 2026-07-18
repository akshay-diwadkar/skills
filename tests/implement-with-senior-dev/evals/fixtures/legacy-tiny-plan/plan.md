# Reject division by zero

## Outcome
Division by zero raises `ValueError` with message `zero divisor`.

## Scope
Only `src/math_ops.py` and `tests/test_math_ops.py` change.

## Change
Guard the divisor before division.

## Verification
Run `python -m pytest -q` and expect all tests to pass.
