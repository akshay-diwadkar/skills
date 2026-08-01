#!/usr/bin/env python3
"""Validate an optimization artifact and any required plan-change request."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from optimization_contract import (
    Diagnostic,
    load_contract,
    load_handoff_contract,
    marker,
    section_names,
)

RECORD_RE = re.compile(r"^- (?P<id>(?:CV|F|B|R|C|V|X|H|E)-\d+): (?P<body>.+)$", re.MULTILINE)
FACT_RE = re.compile(
    r"^- (?P<id>F-\d+): `(?P<path>[^`:]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<observation>.+)$",
    re.MULTILINE,
)
REFERENCE_RE = re.compile(r"\b(?:CV|F|B|R|C|V|X|H|E)-\d+\b")
PLACEHOLDER_RE = re.compile(r"\bReplace(?: with)?\b|existing_(?:anchor|symbol)|`path:1`", re.IGNORECASE)
PERFORMANCE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|ms|s|seconds?|minutes?|calls?|MB|GB|req/s|ops/s)",
    re.IGNORECASE,
)
RAW_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|s|seconds?|minutes?|calls?|MB|GB|req/s|ops/s)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Record:
    identifier: str
    fields: dict[str, str]
    line: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", choices=tuple(contract["paths"]), required=True)
    parser.add_argument("--scope", choices=tuple(contract["scopes"]), required=True)
    parser.add_argument("--stage", choices=tuple(contract["stages"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--handoff-file", type=Path)
    parser.add_argument("report", nargs="?", help="Optimization Markdown file; reads stdin when omitted or '-'.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _sections(text: str) -> list[tuple[str, int, str]]:
    headings = list(re.finditer(r"^## (?P<name>.+)$", text, re.MULTILINE))
    return [
        (
            match.group("name").strip(),
            _line(text, match.start()),
            text[match.end() : headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip(),
        )
        for index, match in enumerate(headings)
    ]


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in body.split(" | "):
        if ": " in item:
            key, value = item.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields


def _records(text: str) -> dict[str, Record]:
    return {
        match.group("id"): Record(match.group("id"), _parse_fields(match.group("body")), _line(text, match.start()))
        for match in RECORD_RE.finditer(text)
    }


def _values(value: str) -> list[str]:
    return [item.strip().strip("`") for item in value.split(",") if item.strip()]


def _metadata(text: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}: (?P<value>.+)$", text, re.MULTILINE)
    return match.group("value").strip() if match else ""


def _read(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _shape(text: str, execution_path: str, scope: str, stage: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    first = next(((number, line.strip()) for number, line in enumerate(text.splitlines(), 1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be an H1 title.", first[0] if first else None))
    expected_marker = marker(execution_path, scope, stage)
    if expected_marker not in text:
        diagnostics.append(Diagnostic("contract.marker.missing", f"Expected exact marker {expected_marker!r}."))
    markers = re.findall(
        r"<!-- optimization-contract: 2; path: (fast|full); scope: (targeted|sweep); stage: (plan|implementation) -->",
        text,
    )
    if markers and markers != [(execution_path, scope, stage)]:
        diagnostics.append(Diagnostic("contract.marker.mismatch", "Artifact marker does not match checker arguments."))
    names = [name for name, _, _ in _sections(text)]
    expected = section_names(execution_path, stage)
    if names != expected:
        diagnostics.append(Diagnostic("shape.sections.order", f"H2 sections must be exactly: {', '.join(expected)}."))
    for name, count in Counter(names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times."))
    for name, line_number, body in _sections(text):
        if not body:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {name!r} is empty.", line_number))
    for match in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("shape.placeholder", f"Unfilled scaffold placeholder {match.group(0)!r}.", _line(text, match.start())))
    return diagnostics


def _facts(text: str, repo_root: Path) -> tuple[list[Diagnostic], dict[str, tuple[str, str]]]:
    diagnostics: list[Diagnostic] = []
    found: dict[str, tuple[str, str]] = {}
    root = repo_root.resolve()
    matches = list(FACT_RE.finditer(text))
    if not matches:
        return [Diagnostic("fact.format", "At least one canonical F-n repository citation is required.")], found
    for match in matches:
        relative = match.group("path").replace("\\", "/")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            diagnostics.append(Diagnostic("fact.path.outside_repo", f"Citation path escapes repository: {relative}.", _line(text, match.start())))
            continue
        if not path.is_file():
            diagnostics.append(Diagnostic("fact.path.missing", f"Cited file does not exist: {relative}.", _line(text, match.start())))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        line_number = int(match.group("line"))
        anchor = match.group("anchor")
        if line_number < 1 or line_number > len(lines):
            diagnostics.append(Diagnostic("fact.line.missing", f"Cited line {line_number} does not exist in {relative}.", _line(text, match.start())))
        elif anchor not in lines[line_number - 1]:
            diagnostics.append(Diagnostic("fact.anchor.missing", f"Anchor {anchor!r} is not on {relative}:{line_number}.", _line(text, match.start())))
        found[match.group("id")] = (relative, anchor)
    return diagnostics, found


def _baseline_diagnostics(records: dict[str, Record]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    contract = load_contract()
    for identifier, record in records.items():
        if not identifier.startswith("B-"):
            continue
        required = {"workflow", "method", "command", "result", "confidence", "evidence"}
        if not required <= record.fields.keys():
            diagnostics.append(Diagnostic("baseline.fields.missing", "B-n is missing required baseline fields.", record.line))
            continue
        method = record.fields["method"]
        if method not in {"command", "static", "blocked"}:
            diagnostics.append(Diagnostic("baseline.method.invalid", "B-n method must be command, static, or blocked.", record.line))
        if record.fields["confidence"] not in contract["ratings"]:
            diagnostics.append(Diagnostic("baseline.confidence.invalid", "B-n confidence must be high, medium, or low.", record.line))
        evidence = _values(record.fields["evidence"])
        if not evidence or any(item not in records or not item.startswith("F-") for item in evidence):
            diagnostics.append(Diagnostic("baseline.evidence.invalid", "B-n evidence must cite existing F-n facts.", record.line))
        if method == "command" and not RAW_UNIT_RE.search(record.fields["result"]):
            diagnostics.append(Diagnostic("baseline.raw_result.missing", "Command baseline must include raw values with units or counts.", record.line))
        if method == "static" and PERFORMANCE_RE.search(record.fields["result"]):
            diagnostics.append(Diagnostic("baseline.static.performance_claim", "Static evidence cannot claim measured performance.", record.line))
        if method == "blocked" and record.fields["confidence"] == "high":
            diagnostics.append(Diagnostic("baseline.blocked.confidence", "Blocked measurement cannot have high confidence.", record.line))
        if re.search(r"\d+(?:\.\d+)?\s*%", record.fields["result"]) and not RAW_UNIT_RE.search(record.fields["result"]):
            diagnostics.append(Diagnostic("baseline.percentage_only", "Percentage claims require raw values and units.", record.line))
    return diagnostics


def _git_fast_state(repo_root: Path, relative: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not (repo_root / relative).is_file():
        diagnostics.append(Diagnostic("fast.fact.missing", "Fast-path fact must cite an existing file."))
        return diagnostics
    dirty = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--", relative],
        capture_output=True,
        text=True,
        check=False,
    )
    if dirty.returncode != 0 or dirty.stdout.strip():
        diagnostics.append(Diagnostic("fast.fact.dirty", "Fast path cannot overlap an existing dirty-worktree change."))
    return diagnostics


def _fast(text: str, scope: str, stage: str, repo_root: Path) -> list[Diagnostic]:
    contract = load_contract()
    diagnostics = _shape(text, "fast", scope, stage)
    if scope != contract["fast"]["scope"] or stage != contract["fast"]["stage"]:
        diagnostics.append(Diagnostic("fast.routing.invalid", "Fast path is targeted implementation only."))
    authorization = _metadata(text, "Authorization").casefold()
    if not authorization.startswith("explicit implementation") or any(term in authorization for term in ("unknown", "guessed", "plan-only")):
        diagnostics.append(Diagnostic("fast.authorization.missing", "Fast path requires the current request's explicit implementation authorization."))
    records = _records(text)
    counts = Counter(identifier.split("-", 1)[0] for identifier in records)
    if counts != Counter(contract["fast"]["exact_record_counts"]):
        diagnostics.append(Diagnostic("fast.records.exact", "Fast artifact must contain exactly one F-n, one B-n, and one C-n record."))
    diagnostics.extend(
        Diagnostic("record.reference.missing", f"Reference {reference} has no matching record.")
        for reference in REFERENCE_RE.findall(text)
        if reference not in records
    )
    fact_diagnostics, facts = _facts(text, repo_root)
    diagnostics.extend(fact_diagnostics)
    diagnostics.extend(_baseline_diagnostics(records))
    baseline = records.get("B-1")
    if baseline and (baseline.fields.get("confidence") != "high" or baseline.fields.get("method") == "blocked"):
        diagnostics.append(Diagnostic("fast.baseline.ineligible", "Fast baseline must be measured or complete bounded-static evidence with high confidence.", baseline.line))
    candidate = records.get("C-1")
    if candidate:
        required = {"band", "eligibility", "evidence", "anchors", "change", "benefit", "verify", "expected", "rollback"}
        if not required <= candidate.fields.keys():
            diagnostics.append(Diagnostic("fast.candidate.fields", "Fast C-1 is missing required decision fields.", candidate.line))
        if candidate.fields.get("band") != "quick-win":
            diagnostics.append(Diagnostic("fast.band.invalid", "Fast path accepts Quick Wins only.", candidate.line))
        eligibility = {}
        for item in _values(candidate.fields.get("eligibility", "")):
            name, separator, value = item.partition("=")
            if separator:
                eligibility[name] = value
        expected_eligibility = set(contract["fast"]["eligibility"])
        if set(eligibility) != expected_eligibility or any(value != "yes" for value in eligibility.values()):
            diagnostics.append(Diagnostic("fast.eligibility.incomplete", "Fast C-1 must affirm every canonical eligibility criterion.", candidate.line))
        if set(_values(candidate.fields.get("evidence", ""))) != {"F-1", "B-1"}:
            diagnostics.append(Diagnostic("fast.evidence.invalid", "Fast C-1 evidence must be exactly F-1 and B-1.", candidate.line))
        expected_anchors = {f"{path}:{anchor}" for path, anchor in facts.values()}
        if set(_values(candidate.fields.get("anchors", ""))) != expected_anchors:
            diagnostics.append(Diagnostic("fast.anchors.invalid", "Fast C-1 must cite the exact F-1 path:symbol anchor.", candidate.line))
        for field in ("change", "benefit", "verify", "expected", "rollback"):
            if candidate.fields.get(field, "").casefold() in {"", "none", "unknown", "tbd", "n/a"}:
                diagnostics.append(Diagnostic(f"fast.{field}.missing", f"Fast C-1 requires a concrete {field}.", candidate.line))
    if len(facts) == 1:
        relative, _ = next(iter(facts.values()))
        diagnostics.extend(_git_fast_state(repo_root, relative))
    return diagnostics


def _coverage(text: str, scope: str, records: dict[str, Record]) -> list[Diagnostic]:
    contract = load_contract()
    diagnostics: list[Diagnostic] = []
    coverage = [record for identifier, record in records.items() if identifier.startswith("CV-")]
    seen: set[tuple[str, str]] = set()
    for record in coverage:
        pair = (record.fields.get("subsystem", ""), record.fields.get("pass", ""))
        if not all(pair):
            diagnostics.append(Diagnostic("coverage.pair.missing", "CV-n requires subsystem and pass.", record.line))
        elif pair in seen:
            diagnostics.append(Diagnostic("coverage.pair.duplicate", f"Coverage pair {pair!r} is duplicated.", record.line))
        seen.add(pair)
        if record.fields.get("status") not in contract["coverage_statuses"]:
            diagnostics.append(Diagnostic("coverage.status.invalid", "CV-n has an invalid status.", record.line))
        if record.fields.get("priority") not in contract["coverage_priorities"]:
            diagnostics.append(Diagnostic("coverage.priority.invalid", "CV-n has an invalid priority.", record.line))
        evidence = _values(record.fields.get("evidence", ""))
        if not evidence or any(item not in records or not item.startswith("F-") for item in evidence):
            diagnostics.append(Diagnostic("coverage.evidence.invalid", "CV-n evidence must cite F-n facts.", record.line))
        if record.fields.get("status") == "deferred" and record.fields.get("resume", "").casefold() in {"", "none", "n/a"}:
            diagnostics.append(Diagnostic("coverage.defer.resume_missing", "Deferred coverage requires a resume action.", record.line))
    subsystems = _values(_metadata(text, "Subsystems"))
    passes = _values(_metadata(text, "Passes"))
    sweep_status = _metadata(text, "Sweep status")
    if scope == "sweep":
        expected = {(subsystem, pass_name) for subsystem in subsystems for pass_name in passes}
        for pair in sorted(expected - seen):
            diagnostics.append(Diagnostic("coverage.matrix.missing", f"Sweep coverage is missing {pair!r}."))
        if len([record for record in coverage if record.fields.get("status") == "candidate"]) > contract["max_sweep_candidates_per_wave"]:
            diagnostics.append(Diagnostic("coverage.wave.limit", "Sweep wave exceeds the candidate depth limit."))
        deferred = [record for record in coverage if record.fields.get("status") == "deferred"]
        if sweep_status != ("incomplete" if deferred else "complete"):
            diagnostics.append(Diagnostic("coverage.sweep_status", "Sweep status does not match deferrals."))
        x_targets = {record.fields.get("target") for identifier, record in records.items() if identifier.startswith("X-")}
        for record in deferred:
            if record.identifier not in x_targets:
                diagnostics.append(Diagnostic("coverage.defer.unlinked", f"Deferred {record.identifier} requires an X-n record.", record.line))
    elif sweep_status != "not-applicable":
        diagnostics.append(Diagnostic("coverage.targeted_status", "Targeted reports require Sweep status: not-applicable."))
    return diagnostics


def _research(records: dict[str, Record]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for identifier, record in records.items():
        if not identifier.startswith("R-"):
            continue
        required = {"component", "version", "source", "finding", "target", "compatibility"}
        if not required <= record.fields.keys():
            diagnostics.append(Diagnostic("research.fields.missing", "R-n is missing required fields.", record.line))
            continue
        if record.fields["source"] == "not-applicable":
            if record.fields["component"] != "not-applicable" or record.fields["version"] != "not-applicable":
                diagnostics.append(Diagnostic("research.not_applicable.invalid", "Not-applicable research must mark component and version likewise.", record.line))
        elif not re.fullmatch(r"https://[^\s|]+", record.fields["source"]):
            diagnostics.append(Diagnostic("research.source.invalid", "R-n source must be a specific HTTPS URL.", record.line))
        if record.fields["source"] != "not-applicable" and record.fields["version"].casefold() in {"", "unknown", "latest", "unresolved"}:
            diagnostics.append(Diagnostic("research.version.unresolved", "Ecosystem research requires a resolved version.", record.line))
        if record.fields["target"] not in records or not record.fields["target"].startswith("B-"):
            diagnostics.append(Diagnostic("research.target.invalid", "R-n target must be an existing B-n.", record.line))
    return diagnostics


def _parse_gates(value: str) -> dict[str, str]:
    return {name.strip(): result.strip() for item in _values(value) for name, separator, result in [item.partition("=")] if separator}


def _candidates(records: dict[str, Record], stage: str, facts: dict[str, tuple[str, str]]) -> list[Diagnostic]:
    contract = load_contract()
    diagnostics: list[Diagnostic] = []
    candidates = [record for identifier, record in records.items() if identifier.startswith("C-")]
    rejected_targets = {record.fields.get("target") for identifier, record in records.items() if identifier.startswith("X-")}
    required = {
        "band", "impact", "confidence", "effort", "risk", "verification-strength", "blast-radius",
        "reversible", "independent", "gates", "evidence", "anchors", "change", "benefit", "verify",
        "rollback", "operational-cost", "experiment",
    }
    promoted: set[str] = set()
    for candidate in candidates:
        fields = candidate.fields
        if not required <= fields.keys():
            diagnostics.append(Diagnostic("candidate.fields.missing", f"{candidate.identifier} is missing canonical fields.", candidate.line))
            continue
        if fields["band"] not in contract["candidate_bands"]:
            diagnostics.append(Diagnostic("candidate.band.invalid", f"{candidate.identifier} has an invalid band.", candidate.line))
            continue
        for name in ("impact", "confidence", "effort", "risk", "blast-radius"):
            if fields[name] not in contract["ratings"]:
                diagnostics.append(Diagnostic("candidate.rating.invalid", f"{candidate.identifier} has invalid {name}.", candidate.line))
        if fields["verification-strength"] not in contract["verification_strengths"]:
            diagnostics.append(Diagnostic("candidate.verification_strength.invalid", f"{candidate.identifier} has invalid verification strength.", candidate.line))
        gates = _parse_gates(fields["gates"])
        if set(gates) != set(contract["promotion_gates"]) or any(value not in {"yes", "no"} for value in gates.values()):
            diagnostics.append(Diagnostic("candidate.gates.incomplete", f"{candidate.identifier} must answer every promotion gate.", candidate.line))
            continue
        evidence = _values(fields["evidence"])
        if not all(any(item.startswith(prefix + "-") for item in evidence) for prefix in ("F", "B", "R")):
            diagnostics.append(Diagnostic("candidate.evidence.incomplete", f"{candidate.identifier} must cite F, B, and R evidence.", candidate.line))
        if any(item not in records for item in evidence):
            diagnostics.append(Diagnostic("candidate.evidence.missing", f"{candidate.identifier} cites missing evidence.", candidate.line))
        fact_anchors = {f"{facts[item][0]}:{facts[item][1]}" for item in evidence if item in facts}
        anchors = set(_values(fields["anchors"]))
        if not anchors or not anchors <= fact_anchors:
            diagnostics.append(Diagnostic("candidate.anchors.invalid", f"{candidate.identifier} anchors must come from its cited F-n records.", candidate.line))
        if fields["verify"] not in records or not fields["verify"].startswith("V-"):
            diagnostics.append(Diagnostic("candidate.verification.missing", f"{candidate.identifier} must cite an existing V-n.", candidate.line))
        if fields["rollback"].casefold() in {"", "none", "unknown", "n/a"}:
            diagnostics.append(Diagnostic("candidate.rollback.missing", f"{candidate.identifier} requires executable rollback.", candidate.line))
        failures = {name for name, value in gates.items() if value == "no"}
        if fields["band"] == "quick-win":
            eligible = (
                not failures and fields["confidence"] == "high" and fields["impact"] in {"high", "medium"}
                and fields["effort"] == fields["risk"] == fields["blast-radius"] == "low"
                and fields["verification-strength"] == "strong"
                and fields["reversible"] == fields["independent"] == "yes"
            )
            if eligible:
                promoted.add(candidate.identifier)
            else:
                diagnostics.append(Diagnostic("candidate.quick_win.ineligible", f"{candidate.identifier} fails Quick Win gates.", candidate.line))
        elif fields["band"] == "strategic-win":
            eligible = (
                not failures and fields["impact"] == "high" and fields["verification-strength"] != "missing"
                and fields["reversible"] == fields["independent"] == "yes"
                and any(fields[name] != "low" for name in ("effort", "risk", "blast-radius"))
            )
            if eligible:
                promoted.add(candidate.identifier)
            else:
                diagnostics.append(Diagnostic("candidate.strategic_win.ineligible", f"{candidate.identifier} fails Strategic Win gates.", candidate.line))
        elif fields["band"] == "investigate":
            if not failures or not failures <= {"baseline", "compatibility"} or fields["experiment"].casefold() in {"", "none", "unknown", "n/a"}:
                diagnostics.append(Diagnostic("candidate.investigate.ineligible", f"{candidate.identifier} is not a valid investigation.", candidate.line))
        elif candidate.identifier not in rejected_targets:
            diagnostics.append(Diagnostic("candidate.rejected.unlinked", f"Rejected {candidate.identifier} requires an X-n record.", candidate.line))
    band_rank = {name: index for index, name in enumerate(contract["candidate_bands"])}
    high = {"high": 0, "medium": 1, "low": 2}
    low = {"low": 0, "medium": 1, "high": 2}
    verification = {"strong": 0, "bounded": 1, "missing": 2}
    def key(record: Record) -> tuple[int, ...]:
        return (
            band_rank.get(record.fields.get("band", ""), 9),
            high.get(record.fields.get("impact", ""), 9),
            high.get(record.fields.get("confidence", ""), 9),
            verification.get(record.fields.get("verification-strength", ""), 9),
            low.get(record.fields.get("effort", ""), 9),
            low.get(record.fields.get("risk", ""), 9),
            low.get(record.fields.get("blast-radius", ""), 9),
            0 if record.fields.get("reversible") == "yes" else 1,
            0 if record.fields.get("independent") == "yes" else 1,
            int(record.identifier.split("-")[1]),
        )
    if [item.identifier for item in candidates] != [item.identifier for item in sorted(candidates, key=key)]:
        diagnostics.append(Diagnostic("candidate.order.invalid", "Candidates do not follow deterministic band and tie-break ordering."))
    for identifier, record in records.items():
        if identifier.startswith("V-"):
            if not {"proves", "method", "expected"} <= record.fields.keys():
                diagnostics.append(Diagnostic("verification.fields.missing", "V-n requires proves, method, and expected.", record.line))
            elif record.fields["proves"] not in records or not record.fields["proves"].startswith("C-"):
                diagnostics.append(Diagnostic("verification.proves.invalid", "V-n must prove an existing C-n.", record.line))
    if stage == "implementation":
        executions = [record for identifier, record in records.items() if identifier.startswith("E-")]
        executed = {record.fields.get("candidate") for record in executions}
        if len(executed) != 1:
            diagnostics.append(Diagnostic("execution.candidate.count", "Implementation must execute exactly one candidate."))
        for execution in executions:
            if execution.fields.get("candidate") not in promoted:
                diagnostics.append(Diagnostic("execution.candidate.ineligible", "E-n candidate must be an eligible win.", execution.line))
            if execution.fields.get("authorization", "").casefold() in {"", "none", "unknown", "plan-only"}:
                diagnostics.append(Diagnostic("execution.authorization.missing", "E-n requires explicit authorization.", execution.line))
        if len([identifier for identifier in records if identifier.startswith("B-")]) < 2:
            diagnostics.append(Diagnostic("execution.comparison.missing", "Full implementation requires before and after B-n records."))
    return diagnostics


def _full(text: str, scope: str, stage: str, repo_root: Path) -> tuple[list[Diagnostic], dict[str, Record], dict[str, tuple[str, str]]]:
    contract = load_contract()
    diagnostics = _shape(text, "full", scope, stage)
    if _metadata(text, "Scope") != scope:
        diagnostics.append(Diagnostic("brief.scope.mismatch", f"Brief must declare Scope: {scope}."))
    if _metadata(text, "Stage") != stage:
        diagnostics.append(Diagnostic("brief.stage.mismatch", f"Brief must declare Stage: {stage}."))
    authorization = _metadata(text, "Authorization")
    if stage == "plan" and authorization != "plan-only":
        diagnostics.append(Diagnostic("authorization.plan_only", "Plan stage requires Authorization: plan-only."))
    if stage == "implementation" and not authorization.casefold().startswith("explicit implementation"):
        diagnostics.append(Diagnostic("authorization.explicit.missing", "Implementation stage requires explicit authorization."))
    for name in ("Goal", "Success criteria", "Constraints", "Exclusions", "Protected behavior"):
        if not _metadata(text, name):
            diagnostics.append(Diagnostic("brief.field.missing", f"Brief requires {name}."))
    records = _records(text)
    identifiers = list(RECORD_RE.finditer(text))
    for identifier, count in Counter(match.group("id") for match in identifiers).items():
        if count > 1:
            diagnostics.append(Diagnostic("record.id.duplicate", f"Record {identifier} is duplicated."))
    required = set(contract["full"]["base_required_prefixes"])
    if stage == "implementation":
        required.update(contract["full"]["implementation_required_prefixes"])
    for prefix in sorted(required):
        if not any(identifier.startswith(prefix + "-") for identifier in records):
            diagnostics.append(Diagnostic("record.required.missing", f"At least one {prefix}-n record is required."))
    if stage == "plan" and any(identifier.startswith("E-") for identifier in records):
        diagnostics.append(Diagnostic("execution.plan_forbidden", "Plan output cannot contain E-n records."))
    for reference in REFERENCE_RE.findall(text):
        if reference not in records:
            diagnostics.append(Diagnostic("record.reference.missing", f"Reference {reference} has no matching record."))
    handoffs = [record for identifier, record in records.items() if identifier.startswith("H-")]
    if len(handoffs) != 1:
        diagnostics.append(Diagnostic("handoff.count", "Exactly one H-n record is required."))
    elif handoffs[0].fields.get("next") not in contract["handoff_states"]:
        diagnostics.append(Diagnostic("handoff.next.invalid", "H-n has an invalid next owner.", handoffs[0].line))
    fact_diagnostics, facts = _facts(text, repo_root)
    diagnostics.extend(fact_diagnostics)
    diagnostics.extend(_coverage(text, scope, records))
    diagnostics.extend(_baseline_diagnostics(records))
    diagnostics.extend(_research(records))
    diagnostics.extend(_candidates(records, stage, facts))
    return diagnostics, records, facts


def _handoff(
    report: str,
    handoff: str | None,
    repo_root: Path,
    records: dict[str, Record],
    facts: dict[str, tuple[str, str]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    h_records = [record for identifier, record in records.items() if identifier.startswith("H-")]
    plan_change = len(h_records) == 1 and h_records[0].fields.get("next") == "plan-change"
    if plan_change and handoff is None:
        return [Diagnostic("handoff.file.required", "plan-change requires --handoff-file.")]
    if not plan_change and handoff is not None:
        return [Diagnostic("handoff.file.unexpected", "A handoff file is valid only for plan-change.")]
    if handoff is None:
        return diagnostics
    contract = load_handoff_contract()
    if "<!-- artifact: request.md; handoff-contract: 1 -->" not in handoff:
        diagnostics.append(Diagnostic("handoff.marker.missing", "request.md requires the exact artifact marker."))
    title = next((line[2:].strip() for line in handoff.splitlines() if line.startswith("# ")), "")
    if title != contract["title"]:
        diagnostics.append(Diagnostic("handoff.title.invalid", f"request.md title must be {contract['title']!r}."))
    names = [name for name, _, _ in _sections(handoff)]
    if names != contract["sections"]:
        diagnostics.append(Diagnostic("handoff.sections.invalid", f"request.md sections must be exactly: {', '.join(contract['sections'])}."))
    for name in contract["required_metadata"]:
        value = _metadata(handoff, name)
        if not value or value.casefold() in {"tbd", "unknown", "deferred", "implicit"}:
            diagnostics.append(Diagnostic("handoff.field.missing", f"request.md requires concrete {name}."))
    selected = h_records[0].fields.get("candidate", "")
    candidate = records.get(selected)
    if not candidate:
        diagnostics.append(Diagnostic("handoff.candidate.missing", "H-n must select an existing C-n."))
        return diagnostics
    if candidate.fields.get("band") != "strategic-win":
        diagnostics.append(Diagnostic("handoff.candidate.band", "plan-change handoff requires a Strategic Win."))
    expected_baselines = [records[item].fields.get("workflow", "") for item in _values(candidate.fields.get("evidence", "")) if item.startswith("B-") and item in records]
    expected = {
        "Goal": _metadata(report, "Goal"),
        "Success criteria": _metadata(report, "Success criteria"),
        "Protected behavior": _metadata(report, "Protected behavior"),
        "Constraints": _metadata(report, "Constraints"),
        "Exclusions": _metadata(report, "Exclusions"),
        "Candidate": selected,
        "Band": candidate.fields.get("band", ""),
        "Mechanism": candidate.fields.get("change", ""),
    }
    if expected_baselines:
        expected["Workflow"] = expected_baselines[0]
    for name, value in expected.items():
        if _metadata(handoff, name) != value:
            diagnostics.append(Diagnostic("handoff.field.mismatch", f"request.md {name} must match this optimization run."))
    handoff_evidence = set(_values(_metadata(handoff, "Evidence")))
    candidate_evidence = set(_values(candidate.fields.get("evidence", "")))
    if handoff_evidence != candidate_evidence:
        diagnostics.append(Diagnostic("handoff.evidence.mismatch", "request.md Evidence must exactly match the winning C-n evidence."))
    tier = _metadata(handoff, "Tier")
    intent = _metadata(handoff, "Intent")
    risk_domains = _values(_metadata(handoff, "Risk domains"))
    if tier not in contract["tiers"]:
        diagnostics.append(Diagnostic("handoff.tier.invalid", "request.md Tier is not accepted by plan-contract v6."))
    if intent not in contract["intents"]:
        diagnostics.append(Diagnostic("handoff.intent.invalid", "request.md Intent is not accepted by plan-contract v6."))
    if risk_domains == ["none"]:
        risk_domains = []
    if any(domain not in contract["risk_domains"] for domain in risk_domains):
        diagnostics.append(Diagnostic("handoff.risk_domain.invalid", "request.md contains an unsupported risk domain."))
    if (tier == "high-risk") != bool(risk_domains):
        diagnostics.append(Diagnostic("handoff.risk_domain.tier", "High-risk tier requires risk domains; other tiers must use none."))
    anchor_matches = re.findall(r"^- Anchor: `(?P<anchor>[^`]+)`$", handoff, re.MULTILINE)
    if not anchor_matches:
        diagnostics.append(Diagnostic("handoff.anchor.missing", "request.md requires at least one literal Anchor line."))
    candidate_anchors = set(_values(candidate.fields.get("anchors", "")))
    fact_anchors = {f"{facts[item][0]}:{facts[item][1]}" for item in _values(candidate.fields.get("evidence", "")) if item in facts}
    for anchor in anchor_matches:
        if anchor not in candidate_anchors or anchor not in fact_anchors:
            diagnostics.append(Diagnostic("handoff.anchor.unbound", f"Anchor {anchor!r} is not present in the winning C/F records."))
    if set(anchor_matches) != candidate_anchors:
        diagnostics.append(Diagnostic("handoff.anchor.incomplete", "request.md must carry every winning candidate anchor exactly once."))
    return diagnostics


def validate(
    text: str,
    execution_path: str,
    scope: str,
    stage: str,
    repo_root: Path,
    handoff_text: str | None = None,
) -> list[Diagnostic]:
    if execution_path == "fast":
        diagnostics = _fast(text, scope, stage, repo_root)
        if handoff_text is not None:
            diagnostics.append(Diagnostic("handoff.file.unexpected", "Fast path cannot emit a plan-change handoff."))
        return diagnostics
    diagnostics, records, facts = _full(text, scope, stage, repo_root)
    diagnostics.extend(_handoff(text, handoff_text, repo_root, records, facts))
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handoff = args.handoff_file.read_text(encoding="utf-8") if args.handoff_file else None
    diagnostics = validate(_read(args.report), args.path, args.scope, args.stage, args.repo_root, handoff)
    if args.format == "json":
        retry = {"argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], "cwd": str(Path.cwd())}
        print(
            json.dumps(
                {
                    "valid": not diagnostics,
                    "diagnostics": [item.to_dict(path=args.report or "stdin", next_command=retry) for item in diagnostics],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    elif diagnostics:
        print("Optimization check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Optimization check passed.")
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
