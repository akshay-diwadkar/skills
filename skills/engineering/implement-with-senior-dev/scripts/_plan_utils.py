"""
Shared utilities for plan validation, receipt verification, fence stripping, and plan finalization.

NOTE: The plan-validation functions (validate_receipt, plan_digest, canonical_plan_body,
finalize_plan_text, strip_fenced_code_blocks, etc.) are duplicated in
plan-with-senior-dev/scripts/_plan_utils.py. Keep them in sync when making changes to
shared plan-handling logic. Bundle-specific functions (canonical_bundle_bytes,
bundle_digest, validate_bundle_receipt) live only here.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None
    is_warning: bool = False

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "is_warning": self.is_warning,
        }

    def __str__(self) -> str:
        prefix = "Warning" if self.is_warning else "Error"
        line_info = f" on line {self.line}" if self.line is not None else ""
        return f"{prefix} [{self.code}]{line_info}: {self.message}"


def read_plan(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def strip_fenced_code_blocks(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in lines:
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
            output.append("")
            continue
        output.append("" if fence_character is not None else line)
    return "\n".join(output)


VALIDATION_PREFIX_RE = re.compile(r"^\s*<!--\s*plan-validation\s*:", re.IGNORECASE)
VALIDATION_RECEIPT_RE = re.compile(
    r"^<!-- plan-validation: 3; sha256: (?P<digest>[0-9a-f]{64}) -->$"
)


def _normalized_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").splitlines()


def receipt_lines(text: str) -> list[tuple[int, str]]:
    return [
        (line_number, line.strip())
        for line_number, line in enumerate(_normalized_lines(text), start=1)
        if VALIDATION_PREFIX_RE.match(line)
    ]


def canonical_plan_body(text: str) -> str:
    """Return LF-normalized plan content with every validation receipt removed."""
    lines = [line for line in _normalized_lines(text) if not VALIDATION_PREFIX_RE.match(line)]
    return "\n".join(lines).rstrip("\n") + "\n"


def plan_digest(text: str) -> str:
    return hashlib.sha256(canonical_plan_body(text).encode("utf-8")).hexdigest()


def validate_receipt(text: str, *, required: bool) -> list[Diagnostic]:
    found = receipt_lines(text)
    if not found:
        return [Diagnostic("finalization.receipt.missing", "Finalized plan requires one validation receipt")] if required else []
    if len(found) > 1:
        return [Diagnostic("finalization.receipt.duplicate", "Plan contains multiple validation receipts", found[1][0])]
    line_number, line = found[0]
    match = VALIDATION_RECEIPT_RE.fullmatch(line)
    if match is None:
        return [Diagnostic("finalization.receipt.malformed", "Validation receipt must use the v3 SHA-256 format", line_number)]
    expected = plan_digest(text)
    if match.group("digest") != expected:
        return [Diagnostic("finalization.receipt.stale", "Validation receipt does not match the canonical plan body", line_number)]
    return []


def finalize_plan_text(text: str) -> str:
    body = canonical_plan_body(text)
    lines = body.rstrip("\n").splitlines()
    receipt = f"<!-- plan-validation: 3; sha256: {plan_digest(body)} -->"
    insertion = next(
        (index + 1 for index, line in enumerate(lines) if re.fullmatch(r"<!-- tier: .+ -->", line.strip())),
        None,
    )
    if insertion is None:
        insertion = next(
            (index + 1 for index, line in enumerate(lines) if line.strip() == "<!-- plan-contract: 3 -->"),
            1,
        )
    lines.insert(insertion, receipt)
    return "\n".join(lines).rstrip("\n") + "\n"


def canonical_bundle_bytes(bundle: dict) -> bytes:
    """Return canonical LF-normalized JSON bytes of bundle with validation_receipt removed."""
    cleaned = {k: v for k, v in bundle.items() if k != "validation_receipt"}
    raw_json = json.dumps(cleaned, indent=2, sort_keys=True)
    normalized = raw_json.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    return normalized.encode("utf-8")


def bundle_digest(bundle: dict) -> str:
    return hashlib.sha256(canonical_bundle_bytes(bundle)).hexdigest()


def validate_bundle_receipt(bundle: dict, *, required: bool = True) -> list[Diagnostic]:
    receipt = bundle.get("validation_receipt")
    if not isinstance(receipt, dict):
        return [Diagnostic("bundle.receipt.missing", "Implementation bundle requires a valid validation receipt.")] if required else []
    if receipt.get("version") != 1 or not isinstance(receipt.get("sha256"), str):
        return [Diagnostic("bundle.receipt.malformed", "Validation receipt must specify version 1 and a SHA-256 digest.")]
    expected = bundle_digest(bundle)
    if receipt.get("sha256") != expected:
        return [Diagnostic("bundle.receipt.stale", "Validation receipt does not match the current bundle state.")]
    return []
