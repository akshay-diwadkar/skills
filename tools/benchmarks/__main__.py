from __future__ import annotations

import argparse
import subprocess
import sys

from .catalog import AUDIT_PATH, render_audit
from .fixtures import ROOT, BenchmarkError, load_manifests


def _validate() -> int:
    manifests = load_manifests()
    print(f"Validated {len(manifests)} benchmark manifests.")
    return 0


def _regenerate(check: bool) -> int:
    command = [sys.executable, str(ROOT / "benchmarks" / "generators" / "generate.py")]
    command.append("--check" if check else "--write")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def _audit(check: bool) -> int:
    rendered = render_audit()
    if check:
        if not AUDIT_PATH.is_file() or AUDIT_PATH.read_text(encoding="utf-8") != rendered:
            print("Fixture audit is stale; run `python -m tools.benchmarks audit`.", file=sys.stderr)
            return 1
    else:
        AUDIT_PATH.write_text(rendered, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and reproduce benchmark fixtures.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    regenerate = subparsers.add_parser("regenerate")
    regenerate.add_argument("--check", action="store_true")
    audit = subparsers.add_parser("audit")
    audit.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate()
        if args.command == "regenerate":
            return _regenerate(args.check)
        return _audit(args.check)
    except (BenchmarkError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
