"""Strict v4 Markdown plan parser and repository-bound validator."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _plan_utils import Diagnostic
from plan_contract import load_contract
from plan_runtime import binding_digest, canonical_json, plan_digest, repo_snapshot

MARKER = "<!-- plan-contract: 4 -->"
META_RE = re.compile(r"^<!-- plan-metadata: (?P<value>\{.*\}) -->$", re.MULTILINE)
REPO_RE = re.compile(r"^<!-- plan-repository: (?P<value>\{.*\}) -->$", re.MULTILINE)
RECEIPT_RE = re.compile(
    r"^<!-- plan-validation: 4; body-sha256: (?P<body>[0-9a-f]{64}); binding-sha256: (?P<binding>[0-9a-f]{64}) -->$",
    re.MULTILINE,
)
ID_RE = re.compile(r"^- (?P<id>(?:SC|F|D|CH|T|C|R|P|B)-\d+):", re.MULTILINE)
FACT_RE = re.compile(
    r"^- (?P<id>F-\d+): path: `(?P<path>[^`]+)` \| lines: (?P<start>\d+)-(?P<end>\d+) \| anchor: `(?P<anchor>[^`]+)` \| excerpt-sha256: `(?P<excerpt>[0-9a-f]{64})` \| file-sha256: `(?P<file>[0-9a-f]{64})` \| observation: (?P<observation>.+)$",
    re.MULTILINE,
)
CHANGE_RE = re.compile(
    r"^- (?P<id>CH-\d+): path: `(?P<path>[^`]+)` \| anchor: `(?P<anchor>[^`]+)` \| status: (?P<status>existing|new) \| evidence: (?P<evidence>F-\d+)(?: \| directory-owner: (?P<owner>F-\d+))? \| change: (?P<change>.+)$",
    re.MULTILINE,
)
SC_RE = re.compile(r"^- SC-\d+: given: .+ \| when: .+ \| then: .+ \| unchanged: .+$", re.MULTILINE)
DECISION_RE = re.compile(
    r"^- D-\d+: selected: .+ \| evidence: (?:F|C)-\d+ \| rejected: .+ \| drawback: .+$", re.MULTILINE
)
TEST_RE = re.compile(r"^- T-\d+: given: .+ \| expect: .+ \| command: `[^`]+`\.?$", re.MULTILINE)
PROP_RE = re.compile(
    r"^- P-\d+: path: `[^`]+` \| surface: .+ \| disposition: (?:changed|test-only|generated|unchanged|out-of-scope) \| (?:owner: CH-\d+|because: F-\d+)\.?$",
    re.MULTILINE,
)
BOUNDARY_RE = re.compile(r"^- B-\d+: class: .+ \| path: F-\d+ \| flow: .+\.$", re.MULTILINE)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _safe(root: Path, raw: str) -> Path | None:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root.resolve())
        return resolved
    except (OSError, ValueError):
        return None


def _metadata(text: str) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    matches = list(META_RE.finditer(text))
    diags: list[Diagnostic] = []
    if len(matches) != 1:
        return None, [Diagnostic("metadata.count", "Plan requires exactly one strict plan-metadata JSON record.")]
    try:
        value = json.loads(matches[0].group("value"))
    except json.JSONDecodeError:
        return None, [
            Diagnostic("metadata.json", "plan-metadata must contain valid JSON.", _line(text, matches[0].start()))
        ]
    contract = load_contract()
    if not isinstance(value, dict):
        return None, [Diagnostic("metadata.type", "plan-metadata must be an object.")]
    for name in ("provisional", "final"):
        item = value.get(name)
        if not isinstance(item, dict):
            diags.append(Diagnostic("metadata.classification", f"metadata.{name} must be an object."))
            continue
        if item.get("intent") not in contract["intents"]:
            diags.append(Diagnostic("metadata.intent", f"metadata.{name}.intent is invalid."))
        domains = item.get("risk_domains")
        if (
            not isinstance(domains, list)
            or any(domain not in contract["risk_domains"] for domain in domains)
            or len(domains) != len(set(domains))
        ):
            diags.append(
                Diagnostic(
                    "metadata.risk_domains", f"metadata.{name}.risk_domains must be a unique list of valid domains."
                )
            )
        if item.get("tier") not in contract["tiers"]:
            diags.append(Diagnostic("metadata.tier", f"metadata.{name}.tier is invalid."))
    if not diags:
        ranks = {"tiny": 0, "standard": 1, "high-risk": 2}
        provisional, final = value["provisional"], value["final"]
        if ranks[final["tier"]] < ranks[provisional["tier"]]:
            diags.append(Diagnostic("metadata.tier.downgrade", "Final tier must not downgrade provisional tier."))
        required = (
            "high-risk" if set(final["risk_domains"]) & set(contract["tier_rules"]["high-risk_domains"]) else None
        )
        if required and final["tier"] != required:
            diags.append(Diagnostic("metadata.tier.domain", "Selected risk domains require high-risk tier."))
    return value, diags


def _records(text: str, prefix: str) -> set[str]:
    return {match.group("id") for match in ID_RE.finditer(text) if match.group("id").startswith(prefix + "-")}


def validate(
    text: str,
    repo_root: Path,
    tier: str | None = None,
    *,
    require_finalized: bool = False,
    baseline: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if text.count(MARKER) != 1:
        return [Diagnostic("contract.marker", "Plan requires exactly one <!-- plan-contract: 4 --> marker.")]
    metadata, meta_diags = _metadata(text)
    diags.extend(meta_diags)
    if metadata is None:
        return diags
    final = metadata["final"]
    if tier and tier != final["tier"]:
        diags.append(Diagnostic("metadata.tier.cli_mismatch", "Command-line tier does not equal metadata.final.tier."))
    contract = load_contract()
    required = contract["tiers"][final["tier"]]["required_ids"]
    for prefix in required:
        if not _records(text, prefix):
            diags.append(Diagnostic("records.missing", f"{final['tier']} plan requires a {prefix}-n record."))
    if len(_records(text, "SC")) != len(SC_RE.findall(text)):
        diags.append(Diagnostic("success.observable", "Each SC-n must define given, when, then, and unchanged."))
    if len(_records(text, "D")) != len(DECISION_RE.findall(text)):
        diags.append(
            Diagnostic("decision.evidence", "Each D-n needs selected, evidence, rejected, and concrete drawback.")
        )
    if len(_records(text, "T")) != len(TEST_RE.findall(text)):
        diags.append(Diagnostic("test.format", "Each T-n must have given, expect, and command."))
    if len(_records(text, "P")) != len(PROP_RE.findall(text)):
        diags.append(Diagnostic("propagation.format", "Each P-n needs a disposition and owner or grounded reason."))
    if len(_records(text, "B")) != len(BOUNDARY_RE.findall(text)):
        diags.append(Diagnostic("boundary.format", "Each B-n needs a boundary class and F-n path."))
    facts = {match.group("id"): match for match in FACT_RE.finditer(text)}
    if len(facts) != len(_records(text, "F")):
        diags.append(
            Diagnostic("evidence.format", "Each F-n must use path, range, anchor, excerpt hash, and file hash.")
        )
    for fact_id, fact in facts.items():
        path = _safe(repo_root, fact.group("path"))
        line = _line(text, fact.start())
        if path is None:
            diags.append(Diagnostic("evidence.outside_repo", f"{fact_id} path escapes repository; repair path.", line))
            continue
        if not path.is_file():
            diags.append(Diagnostic("evidence.missing_file", f"{fact_id} cites missing file; repair path.", line))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        start, end = int(fact.group("start")), int(fact.group("end"))
        if start < 1 or end < start or end > len(lines):
            diags.append(
                Diagnostic("evidence.range", f"{fact_id} range is outside {fact.group('path')}; repair lines.", line)
            )
            continue
        excerpt = "\n".join(lines[start - 1 : end]).encode()
        if fact.group("anchor") not in "\n".join(lines[start - 1 : end]):
            diags.append(Diagnostic("evidence.anchor", f"{fact_id} anchor is absent from its cited range.", line))
        if _sha(path.read_bytes()) != fact.group("file"):
            diags.append(Diagnostic("evidence.file_hash", f"{fact_id} file fingerprint is stale.", line))
        if _sha(excerpt) != fact.group("excerpt"):
            diags.append(
                Diagnostic(
                    "evidence.excerpt_hash", f"{fact_id} observation fingerprint is stale or contradictory.", line
                )
            )
    changes = {match.group("id"): match for match in CHANGE_RE.finditer(text)}
    if len(changes) != len(_records(text, "CH")):
        diags.append(Diagnostic("change.format", "Each CH-n needs strict path, anchor, status, and evidence fields."))
    for change_id, change in changes.items():
        path = _safe(repo_root, change.group("path"))
        line = _line(text, change.start())
        if path is None:
            diags.append(Diagnostic("change.outside_repo", f"{change_id} target escapes repository.", line))
            continue
        if change.group("evidence") not in facts:
            diags.append(Diagnostic("change.evidence", f"{change_id} must cite an existing F-n.", line))
        if change.group("status") == "existing":
            if not path.is_file():
                diags.append(Diagnostic("change.missing", f"{change_id} is existing but its target is absent.", line))
            elif change.group("anchor") not in path.read_text(encoding="utf-8", errors="replace"):
                diags.append(Diagnostic("change.anchor", f"{change_id} anchor is absent from target.", line))
        else:
            if path.exists():
                diags.append(Diagnostic("change.new_exists", f"{change_id} is new but target already exists.", line))
            if not path.parent.exists() and not change.group("owner"):
                diags.append(
                    Diagnostic(
                        "change.new_directory_owner",
                        f"{change_id} creates a directory and needs directory-owner: F-n.",
                        line,
                    )
                )
    obligations = "\n".join(line for line in text.splitlines() if line.startswith("- O-"))
    for domain in final["risk_domains"]:
        for obligation in contract["domain_obligations"].get(domain, []):
            if obligation not in obligations:
                diags.append(
                    Diagnostic(
                        f"domain.{domain}.{obligation}_missing",
                        f"risk domain `{domain}` requires obligation `{obligation}` in Domain Obligations.",
                    )
                )
    attacks = "\n".join(line for line in text.splitlines() if line.startswith("- A-"))
    attacks_required = list(contract["always_required_attacks"])
    for domain in final["risk_domains"]:
        attacks_required.extend(contract["domain_attacks"].get(domain, []))
    for attack in attacks_required:
        if f"A-{attack}:" not in attacks:
            diags.append(Diagnostic("attack.missing", f"Required applicability-driven attack A-{attack} is absent."))
    trace = next((part for part in text.split("## Traceability", 1)[1:]), "")
    for item in _records(text, "SC") | _records(text, "C") | _records(text, "CH") | _records(text, "T"):
        if item not in trace:
            diags.append(Diagnostic("trace.unmapped", f"{item} is not mapped in Traceability."))
    repo_matches = list(REPO_RE.finditer(text))
    receipts = list(RECEIPT_RE.finditer(text))
    if require_finalized:
        if len(repo_matches) != 1:
            diags.append(Diagnostic("binding.missing", "Finalized plan requires one plan-repository binding."))
        if len(receipts) != 1:
            diags.append(Diagnostic("receipt.missing", "Finalized plan requires one v4 receipt."))
        if repo_matches and receipts:
            try:
                binding = json.loads(repo_matches[0].group("value"))
            except json.JSONDecodeError:
                diags.append(Diagnostic("binding.json", "plan-repository must contain valid JSON."))
                binding = {}
            receipt = receipts[0]
            if receipt.group("body") != plan_digest(text):
                diags.append(Diagnostic("receipt.stale", "Receipt body hash does not match plan."))
            if receipt.group("binding") != binding_digest(binding):
                diags.append(Diagnostic("receipt.binding", "Receipt binding hash does not match repository binding."))
            current = repo_snapshot(repo_root)
            if canonical_json({k: binding.get(k) for k in ("repository_id", "git_head", "dirty")}) != canonical_json(
                {k: current.get(k) for k in ("repository_id", "git_head", "dirty")}
            ):
                diags.append(
                    Diagnostic(
                        "binding.repository_stale",
                        "Repository identity, revision, or dirty state differs from finalization.",
                    )
                )
        if baseline is not None and not canonical_json(repo_snapshot(repo_root)) == canonical_json(baseline):
            diags.append(
                Diagnostic(
                    "planning.worktree_mutated", "Target repository changed during planning; finalization fails closed."
                )
            )
    return diags


def binding_for(text: str, repo_root: Path) -> dict[str, Any]:
    snapshot = repo_snapshot(repo_root)
    return {
        "repository_id": snapshot["repository_id"],
        "git_head": snapshot["git_head"],
        "dirty": snapshot["dirty"],
        "tree_sha256": _sha(canonical_json(snapshot["tree"]).encode()),
        "plan_body_sha256": plan_digest(text),
    }
