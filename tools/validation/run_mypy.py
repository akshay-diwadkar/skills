#!/usr/bin/env python3
"""Run mypy in isolated skill scopes discovered from the filesystem."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "skills"


def run_mypy_group(label: str, targets: list[Path], extra_paths: list[Path] | None = None) -> bool:
    existing = [str(path.relative_to(ROOT)) for path in targets if path.exists()]
    if not existing:
        return True
    env = dict(os.environ)
    if extra_paths:
        env["MYPYPATH"] = os.pathsep.join(str(path) for path in extra_paths)
    result = subprocess.run([sys.executable, "-m", "mypy", "--no-incremental", *existing], cwd=ROOT, env=env)
    if result.returncode:
        print(f"Mypy check failed for {label}", file=sys.stderr)
        return False
    return True


def discover_skill_scopes() -> list[tuple[str, list[Path], list[Path]]]:
    return [
        (
            f"{skill_dir.parent.name}/{skill_dir.name}",
            [skill_dir, ROOT / "tests" / "skills" / skill_dir.name],
            [skill_dir / "scripts"],
        )
        for domain_dir in sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
        for skill_dir in sorted(
            path for path in domain_dir.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
        )
    ]


def main() -> int:
    failures: list[str] = []
    for name, targets, extra_paths in discover_skill_scopes():
        if not run_mypy_group(f"skill: {name}", targets, extra_paths):
            failures.append(name)
    tooling = [
        ROOT / "tools" / "validation",
        ROOT / "tools" / "benchmarks",
        ROOT / "tools" / "diagnostics",
        ROOT / "tools" / "skill_protocol",
        ROOT / "tools" / "skill_cli.py",
        ROOT / "tests" / "benchmarks",
        ROOT / "tests" / "repository",
        ROOT / "tests" / "integration",
        ROOT / "tests" / "skill_protocol",
    ]
    if not run_mypy_group("repository tooling", tooling):
        failures.append("repository tooling")
    if failures:
        print("Mypy failures: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("All mypy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
