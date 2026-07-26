"""Copy the canonical plan-contract runtime into standalone skill packages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "plan_contract_runtime.py"
TARGETS = (
    ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py",
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_runtime.py",
    ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_runtime.py",
)


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    for target in TARGETS:
        target.write_text(source, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
