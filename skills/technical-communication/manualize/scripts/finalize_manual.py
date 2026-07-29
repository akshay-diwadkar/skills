#!/usr/bin/env python3
"""Validate and atomically finalize a source-bound manual."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from check_manual import load_bundle, validate_manual
from check_manual_language import collect_diagnostics


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _write_atomic(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def finalize(repo_root: Path, bundle_path: Path, manual_path: Path) -> tuple[int, dict[str, Any]]:
    bundle = load_bundle(bundle_path)
    if bundle["operation"] != "write":
        return 1, {"status": "invalid", "error": "Only a write bundle can receive a validation receipt"}
    manual_bytes = manual_path.read_bytes()
    manual_text = manual_bytes.decode("utf-8")
    language = collect_diagnostics(manual_text, bundle["profile"], bundle["glossary"])
    semantic = validate_manual(manual_text, bundle, repo_root)
    language_pass = not any(item["severity"] == "error" for item in language)
    semantic_pass = not semantic
    if not language_pass or not semantic_pass:
        return 1, {
            "status": "invalid",
            "language_pass": language_pass,
            "semantic_pass": semantic_pass,
            "language_violations": language,
            "semantic_errors": semantic,
        }

    body = dict(bundle)
    body.pop("validation_receipt", None)
    manual_hash = _digest(manual_bytes)
    receipt = {
        "contract_version": body["contract_version"],
        "manual_hash": manual_hash,
        "bundle_hash": _digest(_canonical(body)),
        "language_pass": True,
        "semantic_pass": True,
        "receipt": "validated",
    }
    finalized = {**body, "validation_receipt": receipt}
    _write_atomic(bundle_path, (json.dumps(finalized, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0, {
        "status": "final",
        "manual_hash": manual_hash,
        "language_pass": True,
        "semantic_pass": True,
        "receipt": "validated",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("manual", type=Path)
    args = parser.parse_args(argv)
    try:
        status, result = finalize(args.repo_root, args.bundle, args.manual)
    except (OSError, UnicodeError, ValueError) as exc:
        status, result = 2, {"status": "invalid", "error": str(exc)}
    print(json.dumps(result, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
