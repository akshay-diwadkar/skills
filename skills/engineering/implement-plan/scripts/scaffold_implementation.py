#!/usr/bin/env python3
"""Create a versioned implementation-run bundle in ignored or temporary storage."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from implementation_contract import scaffold_bundle


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    run_id = args.run_id or uuid.uuid4().hex[:12]
    try:
        bundle = scaffold_bundle(args.repo_root.resolve(), args.plan.resolve(), args.output.resolve(), run_id)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    args.output.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
