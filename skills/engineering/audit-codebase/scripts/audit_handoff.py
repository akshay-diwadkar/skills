"""Render the immutable audit-to-publication handoff."""
from __future__ import annotations
import hashlib, json
from typing import Any

def render(bundle: dict[str, Any]) -> str:
    context = bundle["audit_context"]
    issues = [c for c in bundle["candidates"] if c["decision"] == "accepted"]
    lines = ["# Audit Issue Handoff", "", "## Audit Context", "", f"- Target: `{context['target']}`", f"- Commit: `{context['commit']}`", f"- Dirty worktree: `{context['dirty_worktree']}`", "- Limitations:"]
    lines += [f"  - {item}" for item in context["limitations"]] or ["  - None"]
    if not issues: lines += ["", "## Issues", "", "No accepted findings."]
    for c in issues:
        labels = next((issue["labels"] for issue in bundle.get("issues", []) if issue.get("candidate_id") == c["id"]), ["audit", c["category"]])
        lines += ["", f"## Issue {c['id']}: {c['title']}", "", f"- Labels: {', '.join(labels)}", f"- Severity: {c['severity']}", f"- Category: {c['category']}", f"- Confidence: {c['confidence']}", "", "### Summary", c['summary'], "", "### Impact", c['impact'], "", "### Root Cause", c['root_cause'], "", "### Evidence"]
        lines += [f"- {e['location']}: {e['observation']}" for e in c['evidence']]
        lines += ["", "### Verification"] + [f"- {x}" for x in c['verification']] + ["", "### Acceptance Criteria"] + [f"- [ ] {x}" for x in c['acceptance_criteria']]
    body = "\n".join(lines) + "\n"
    return f"<!-- audit-handoff: 1; sha256: {hashlib.sha256(body.encode()).hexdigest()} -->\n" + body
