#!/usr/bin/env python3
"""Atomically save and resume in-progress audit bundle checkpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from audit_bundle import SCHEMA_VERSION, AuditBundleError, read_json

PHASE_FIELDS = {
    "audit_context": ("audit_context", "repository_inventory"),
    "risk_surfaces": ("risk_surfaces",),
    "coverage": ("coverage", "deep_analysis"),
    "candidates": ("candidates", "rejects"),
    "issues": ("issues",),
}


def bundle_identity(bundle: Any) -> tuple[str, str]:
    if not isinstance(bundle, dict):
        raise AuditBundleError("checkpoint input must be a JSON object")
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise AuditBundleError(f"schema_version must be {SCHEMA_VERSION}")

    context = bundle.get("audit_context")
    if not isinstance(context, dict):
        raise AuditBundleError("audit_context must be an object")
    target = context.get("target")
    commit = context.get("commit")
    if not isinstance(target, str) or not target.strip():
        raise AuditBundleError("audit_context.target must be a non-empty string")
    if not isinstance(commit, str) or not commit.strip():
        raise AuditBundleError("audit_context.commit must be a non-empty string")
    return target.strip(), commit.strip()


def require_phase_fields(bundle: dict[str, Any], phase: str) -> None:
    missing = [field for field in PHASE_FIELDS[phase] if field not in bundle]
    if missing:
        raise AuditBundleError(
            f"cannot checkpoint phase {phase!r}; missing field(s): {', '.join(missing)}"
        )


def read_checkpoint(path: Path, target: str, commit: str) -> dict[str, Any]:
    bundle = read_json(path)
    checkpoint_target, checkpoint_commit = bundle_identity(bundle)
    if checkpoint_target != target or checkpoint_commit != commit:
        raise AuditBundleError(
            "checkpoint target and commit do not match the current audit "
            f"(found {checkpoint_target}@{checkpoint_commit}, expected {target}@{commit})"
        )
    assert isinstance(bundle, dict)
    return bundle


def write_checkpoint(path: Path, bundle: dict[str, Any], phase: str) -> None:
    target, commit = bundle_identity(bundle)
    require_phase_fields(bundle, phase)
    if path.exists():
        read_checkpoint(path, target, commit)

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(bundle, handle, indent=2)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            os.remove(temporary_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save or resume an audit bundle checkpoint.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    save = subparsers.add_parser("save", help="Atomically save an in-progress audit bundle.")
    save.add_argument("--checkpoint", required=True, help="Checkpoint JSON path.")
    save.add_argument("--input", required=True, help="In-progress audit bundle JSON path.")
    save.add_argument("--phase", required=True, choices=PHASE_FIELDS, help="Completed audit phase.")

    resume = subparsers.add_parser("resume", help="Read a matching audit bundle checkpoint.")
    resume.add_argument("--checkpoint", required=True, help="Checkpoint JSON path.")
    resume.add_argument("--target", required=True, help="Expected audit target.")
    resume.add_argument("--commit", required=True, help="Expected audited commit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checkpoint = Path(args.checkpoint)
    try:
        if args.command == "save":
            bundle = read_json(Path(args.input))
            if not isinstance(bundle, dict):
                raise AuditBundleError("checkpoint input must be a JSON object")
            write_checkpoint(checkpoint, bundle, args.phase)
            print(f"Saved {args.phase} checkpoint to {checkpoint}")
            return 0

        bundle = read_checkpoint(checkpoint, args.target, args.commit)
        print(json.dumps(bundle, indent=2))
        return 0
    except AuditBundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
