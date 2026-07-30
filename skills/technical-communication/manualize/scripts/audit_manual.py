#!/usr/bin/env python3
"""Run authoritative manual validators and emit a read-only audit receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_sources(bundle: Path, repo_root: Path) -> list[Path]:
    try:
        payload: Any = json.loads(bundle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    values = payload.get("sources", []) if isinstance(payload, dict) else []
    paths: list[Path] = []
    for item in values if isinstance(values, list) else []:
        raw = item.get("path") if isinstance(item, dict) else None
        if isinstance(raw, str):
            candidate = Path(raw)
            paths.append((repo_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve())
    return [path for path in paths if path.is_file()]


def _run(script: str, *args: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    try:
        payload: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    return {"returncode": result.returncode, "result": payload}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--glossary", type=Path, required=True)
    parser.add_argument("--profile", choices=("strict", "standard"), required=True)
    parser.add_argument("manual", type=Path)
    args = parser.parse_args(argv)

    paths = [args.manual.resolve(), args.bundle.resolve(), args.glossary.resolve()]
    paths.extend(_bound_sources(args.bundle.resolve(), args.repo_root.resolve()))
    before = {str(path): _sha256(path) for path in paths}
    language = _run(
        "check_manual_language.py",
        "--profile",
        args.profile,
        "--glossary",
        str(args.glossary.resolve()),
        str(args.manual.resolve()),
    )
    semantic = _run(
        "check_manual.py",
        "--repo-root",
        str(args.repo_root.resolve()),
        "--bundle",
        str(args.bundle.resolve()),
        str(args.manual.resolve()),
    )
    after = {str(path): _sha256(path) for path in paths}
    receipt = [
        {
            "artifact": path,
            "before_sha256": before[path],
            "after_sha256": after[path],
            "unchanged": before[path] == after[path],
        }
        for path in before
    ]
    unchanged = all(item["unchanged"] for item in receipt)
    print(
        json.dumps(
            {
                "status": "pass" if unchanged and not language["returncode"] and not semantic["returncode"] else "fail",
                "language": language,
                "semantic": semantic,
                "read_only_receipt": receipt,
                "limitations": ["Validation does not establish factual truth beyond supplied sources."],
            },
            sort_keys=True,
        )
    )
    return 0 if unchanged else 2


if __name__ == "__main__":
    raise SystemExit(main())
