"""Render the immutable audit-to-publication handoff."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

RECEIPT_RE = re.compile(r"^<!-- audit-handoff: 1; sha256: ([0-9a-f]{64}) -->$")
RESERVED_LINE_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def _scalar(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _assert_safe(value: str, field: str) -> None:
    if RESERVED_LINE_RE.search(value) or "<!-- audit-handoff:" in value:
        raise ValueError(f"{field} contains a reserved handoff delimiter")


def render(bundle: dict[str, Any]) -> str:
    """Render one deterministic, receipt-sealed Markdown handoff."""
    context = bundle["audit_context"]
    issues = [candidate for candidate in bundle["candidates"] if candidate["decision"] == "accepted"]
    lines = [
        "# Audit Issue Handoff",
        "",
        "## Audit Context",
        "",
        f"- Target: {_scalar(context['target'])}",
        f"- Commit: {_scalar(context['commit'])}",
        f"- Dirty worktree: {_scalar(context['dirty_worktree'])}",
        f"- Limitations: {_scalar(context['limitations'])}",
        f"- Issue count: {len(issues)}",
    ]
    if not issues:
        lines.extend(["", "## Issues", "", "No accepted findings."])
    for candidate in issues:
        _assert_safe(candidate["id"], f"candidates[{candidate['id']}].id")
        for field in ("title", "summary", "impact", "root_cause", "affected_workflow"):
            _assert_safe(candidate[field], f"candidates[{candidate['id']}].{field}")
        for item in candidate["evidence"]:
            _assert_safe(item["location"], f"candidates[{candidate['id']}].evidence.location")
            _assert_safe(item["observation"], f"candidates[{candidate['id']}].evidence.observation")
        for field in ("verification", "acceptance_criteria"):
            for item in candidate[field]:
                _assert_safe(item, f"candidates[{candidate['id']}].{field}")
        lines.extend(
            [
                "",
                f"## Issue {candidate['id']}",
                "",
                f"- Title: {_scalar(candidate['title'])}",
                f"- Labels: {_scalar(candidate['labels'])}",
                f"- Severity: {_scalar(candidate['severity'])}",
                f"- Category: {_scalar(candidate['category'])}",
                f"- Confidence: {_scalar(candidate['confidence'])}",
                f"- Affected workflow: {_scalar(candidate['affected_workflow'])}",
                "",
                "### Summary",
                "",
                candidate["summary"],
                "",
                "### Impact",
                "",
                candidate["impact"],
                "",
                "### Root Cause",
                "",
                candidate["root_cause"],
                "",
                "### Evidence",
                "",
            ]
        )
        lines.extend(f"- {item['location']}: {item['observation']}" for item in candidate["evidence"])
        lines.extend(["", "### Verification", ""])
        lines.extend(f"- {item}" for item in candidate["verification"])
        lines.extend(["", "### Acceptance Criteria", ""])
        lines.extend(f"- [ ] {item}" for item in candidate["acceptance_criteria"])
    body = "\n".join(lines) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"<!-- audit-handoff: 1; sha256: {digest} -->\n{body}"


def verify_receipt(text: str) -> str:
    """Return the receipt-free body after verifying exact content integrity."""
    receipt, separator, body = text.partition("\n")
    match = RECEIPT_RE.fullmatch(receipt)
    if not separator or match is None:
        raise ValueError("handoff receipt is missing or malformed")
    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != match.group(1):
        raise ValueError("handoff receipt does not match content")
    return body
