#!/usr/bin/env python3
"""Atomically validate and seal the sole ideate handoff artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ideas_contract import Diagnostic, compute_digest, seal_body, validate_ideas  # noqa: E402

RECEIPT_PREFIX = "<!-- ideas-handoff:"
RECEIPT_RE = re.compile(r"^<!-- ideas-handoff: 1; sha256: ([0-9a-f]{64}) -->$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _receipt_free(text: str) -> str:
    """Strip a valid receipt line and return the body, or raise ValueError on tampered receipt."""
    first, separator, body = text.partition("\n")
    if first.startswith(RECEIPT_PREFIX):
        match = RECEIPT_RE.fullmatch(first)
        if match is None or not separator:
            raise ValueError("ideas handoff receipt format is invalid")
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != match.group(1):
            raise ValueError("ideas handoff receipt digest does not match content")
        return body
    return text


def _with_receipt(body: str) -> str:
    digest = compute_digest(body)
    return f"<!-- ideas-handoff: 1; sha256: {digest} -->\n{body}"


def _write_atomic(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
            temporary_name = tmp.name
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _retry_command() -> dict[str, Any]:
    return {
        "argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "cwd": str(Path.cwd()),
    }


def _emit_errors(diagnostics: list[Diagnostic], draft_path: Path) -> None:
    retry = _retry_command()
    print(
        json.dumps(
            [d.as_dict(path=draft_path, next_command=retry) for d in diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    # --- Validate paths ---
    if not args.repo_root.is_absolute() or not args.repo_root.exists():
        parser.error("--repo-root must be an absolute existing directory")
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be absolute")
    if not args.draft.is_file():
        parser.error("--draft must be a readable Markdown file")

    # Draft and output dir must be outside the skill dir
    try:
        args.draft.resolve().relative_to(SKILL_ROOT.resolve())
        parser.error("--draft must be outside the installed skill directory")
    except ValueError:
        pass
    try:
        args.output_dir.resolve().relative_to(SKILL_ROOT.resolve())
        parser.error("--output-dir must be outside the installed skill directory")
    except ValueError:
        pass

    # --- Read and strip receipt ---
    try:
        raw = args.draft.read_text(encoding="utf-8")
        body = _receipt_free(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(
            json.dumps(
                {"valid": False, "diagnostics": [{"code": "ideas.receipt_invalid", "message": str(exc)}]},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    # --- Validate ---
    diagnostics = validate_ideas(body, repo_root=args.repo_root)
    if diagnostics:
        _emit_errors(diagnostics, args.draft)
        return 1

    # --- Normalize and seal ---
    normalized = seal_body(body)
    sealed = _with_receipt(normalized)

    # --- Check output directory ---
    destination = args.output_dir.resolve() / "ideas.md"
    if destination.parent.is_dir():
        extras = [p for p in destination.parent.iterdir() if p.resolve() != destination.resolve()]
        if extras:
            extra_names = [p.name for p in extras]
            print(
                json.dumps(
                    {
                        "valid": False,
                        "diagnostics": [
                            {
                                "code": "ideas.output_not_exclusive",
                                "message": f"output directory contains files other than ideas.md: {extra_names}",
                            }
                        ],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 1

    # --- Atomic write ---
    _write_atomic(destination, sealed)
    print(json.dumps({"status": "sealed", "path": str(destination)}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
