#!/usr/bin/env python3
"""Validate an optimization report against the canonical contract and repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from optimization_contract import Diagnostic, load_contract, marker, section_names

RECORD_RE = re.compile(r"^- (?P<id>(?:CV|F|B|R|C|V|X|H|E)-\d+): (?P<body>.+)$", re.MULTILINE)
FACT_RE = re.compile(
    r"^- (?P<id>F-\d+): `(?P<path>[^`:]+):(?P<line>\d+)` \| anchor: `(?P<anchor>[^`]+)` \| observation: (?P<observation>.+)$",
    re.MULTILINE,
)
REFERENCE_RE = re.compile(r"\b(?:CV|F|B|R|C|V|X|H|E)-\d+\b")
PLACEHOLDER_RE = re.compile(r"\bReplace(?: with)?\b|existing_anchor|`path:1`")
URL_RE = re.compile(r"https://[^\s|]+")


@dataclass(frozen=True)
class Record:
    identifier: str
    fields: dict[str, str]
    line: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=tuple(contract["scopes"]), required=True)
    parser.add_argument("--stage", choices=tuple(contract["stages"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("path", nargs="?", help="Optimization Markdown file; reads stdin when omitted or '-'.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def read_report(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


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


def _section(text: str, name: str) -> str:
    return next((body for section_name, _, body in _sections(text) if section_name == name), "")


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in body.split(" | "):
        if ": " not in item:
            continue
        key, value = item.split(": ", 1)
        fields[key.strip()] = value.strip()
    return fields


def _records(text: str) -> dict[str, Record]:
    return {
        match.group("id"): Record(match.group("id"), _parse_fields(match.group("body")), _line(text, match.start()))
        for match in RECORD_RE.finditer(text)
    }


def _values(line: str) -> list[str]:
    return [item.strip() for item in line.split(",") if item.strip()]


def _metadata(text: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}: (?P<value>.+)$", text, re.MULTILINE)
    return match.group("value").strip() if match else ""


def _validate_shape(text: str, scope: str, stage: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    first = next(((number, line.strip()) for number, line in enumerate(text.splitlines(), 1) if line.strip()), None)
    if first is None or not first[1].startswith("# "):
        diagnostics.append(Diagnostic("shape.title.missing", "First non-empty line must be an H1 title.", first[0] if first else None))
    expected_marker = marker(scope, stage)
    if expected_marker not in text:
        diagnostics.append(Diagnostic("contract.marker.missing", f"Expected exact marker {expected_marker!r}."))
    marker_matches = re.findall(r"<!-- optimization-contract: 1; scope: (targeted|sweep); stage: (plan|implementation) -->", text)
    if marker_matches and marker_matches != [(scope, stage)]:
        diagnostics.append(Diagnostic("contract.marker.mismatch", "Report marker does not match the checker scope and stage."))

    parsed = _sections(text)
    names = [name for name, _, _ in parsed]
    expected = section_names(stage)
    if names != expected:
        diagnostics.append(Diagnostic("shape.sections.order", f"H2 sections must be exactly: {', '.join(expected)}."))
    for name, count in Counter(names).items():
        if count > 1:
            diagnostics.append(Diagnostic("shape.section.duplicate", f"Section {name!r} appears {count} times."))
    for name, line_number, body in parsed:
        if not body:
            diagnostics.append(Diagnostic("shape.section.empty", f"Section {name!r} is empty.", line_number))
    for match in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("shape.placeholder", f"Unfilled scaffold placeholder {match.group(0)!r}.", _line(text, match.start())))

    if _metadata(text, "Scope") != scope:
        diagnostics.append(Diagnostic("brief.scope.mismatch", f"Brief must declare '- Scope: {scope}'."))
    if _metadata(text, "Stage") != stage:
        diagnostics.append(Diagnostic("brief.stage.mismatch", f"Brief must declare '- Stage: {stage}'."))
    authorization = _metadata(text, "Authorization")
    if stage == "plan" and authorization != "plan-only":
        diagnostics.append(Diagnostic("authorization.plan_only", "Plan stage must declare exactly '- Authorization: plan-only'."))
    if stage == "implementation" and (
        not authorization.casefold().startswith("explicit implementation")
        or any(term in authorization.casefold() for term in ("unknown", "none", "not requested"))
    ):
        diagnostics.append(Diagnostic("authorization.explicit.missing", "Implementation stage must name explicit implementation authorization."))
    if stage == "plan" and re.search(r"\bimplementation (?:is )?complete\b", text, re.IGNORECASE):
        diagnostics.append(Diagnostic("authorization.plan_mutation_claim", "Plan-stage output must not claim implementation completed."))
    return diagnostics


def _validate_records(text: str, scope: str, stage: str) -> list[Diagnostic]:
    contract = load_contract()
    diagnostics: list[Diagnostic] = []
    identifiers = [match.group("id") for match in RECORD_RE.finditer(text)]
    records = _records(text)
    for identifier, count in Counter(identifiers).items():
        if count > 1:
            diagnostics.append(Diagnostic("record.id.duplicate", f"Record {identifier} appears {count} times."))
    required = set(contract["base_required_prefixes"])
    if stage == "implementation":
        required.update(contract["implementation_required_prefixes"])
    for prefix in sorted(required):
        if not any(identifier.startswith(f"{prefix}-") for identifier in identifiers):
            diagnostics.append(Diagnostic("record.required.missing", f"At least one {prefix}-n record is required."))
    if stage == "plan" and any(identifier.startswith("E-") for identifier in identifiers):
        diagnostics.append(Diagnostic("execution.plan_forbidden", "Plan-stage output must not contain E-n execution records."))
    for reference in REFERENCE_RE.findall(text):
        if reference not in records:
            diagnostics.append(Diagnostic("record.reference.missing", f"Reference {reference} has no matching record."))

    handoffs = [record for identifier, record in records.items() if identifier.startswith("H-")]
    if len(handoffs) != 1:
        diagnostics.append(Diagnostic("handoff.count", "Exactly one H-n handoff record is required."))
    else:
        handoff = handoffs[0]
        if handoff.fields.get("stage") != stage:
            diagnostics.append(Diagnostic("handoff.stage.mismatch", f"H-n stage must be {stage}.", handoff.line))
        if handoff.fields.get("next") not in contract["handoff_states"]:
            diagnostics.append(Diagnostic("handoff.next.invalid", "H-n must select one canonical next owner.", handoff.line))
        candidate_id = handoff.fields.get("candidate", "")
        if candidate_id not in records or not candidate_id.startswith("C-"):
            diagnostics.append(Diagnostic("handoff.candidate.missing", "H-n candidate must reference an existing C-n.", handoff.line))
    return diagnostics


def _validate_facts(text: str, repo_root: Path) -> list[Diagnostic]:
    matches = list(FACT_RE.finditer(text))
    if not matches:
        return [Diagnostic("fact.format", "At least one canonical F-n repository citation is required.")]
    diagnostics: list[Diagnostic] = []
    root = repo_root.resolve()
    for match in matches:
        path = (root / match.group("path")).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            diagnostics.append(Diagnostic("fact.path.outside_repo", f"Citation path escapes repository: {match.group('path')}.", _line(text, match.start())))
            continue
        if not path.is_file():
            diagnostics.append(Diagnostic("fact.path.missing", f"Cited file does not exist: {match.group('path')}.", _line(text, match.start())))
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        line_number = int(match.group("line"))
        if line_number < 1 or line_number > len(lines):
            diagnostics.append(Diagnostic("fact.line.missing", f"Cited line {line_number} does not exist in {match.group('path')}.", _line(text, match.start())))
        elif match.group("anchor") not in lines[line_number - 1]:
            diagnostics.append(Diagnostic("fact.anchor.missing", f"Anchor {match.group('anchor')!r} is not on {match.group('path')}:{line_number}.", _line(text, match.start())))
    return diagnostics


def _validate_coverage(text: str, scope: str) -> list[Diagnostic]:
    contract = load_contract()
    records = _records(text)
    coverage = [record for identifier, record in records.items() if identifier.startswith("CV-")]
    diagnostics: list[Diagnostic] = []
    seen_pairs: set[tuple[str, str]] = set()
    for record in coverage:
        fields = record.fields
        pair = (fields.get("subsystem", ""), fields.get("pass", ""))
        if not all(pair):
            diagnostics.append(Diagnostic("coverage.pair.missing", "CV-n requires subsystem and pass fields.", record.line))
        elif pair in seen_pairs:
            diagnostics.append(Diagnostic("coverage.pair.duplicate", f"Coverage pair {pair!r} appears more than once.", record.line))
        seen_pairs.add(pair)
        if fields.get("status") not in contract["coverage_statuses"]:
            diagnostics.append(Diagnostic("coverage.status.invalid", "CV-n has an invalid terminal status.", record.line))
        if fields.get("priority") not in contract["coverage_priorities"]:
            diagnostics.append(Diagnostic("coverage.priority.invalid", "CV-n priority must be high, medium, or low.", record.line))
        evidence = _values(fields.get("evidence", ""))
        if not evidence or any(not item.startswith("F-") for item in evidence):
            diagnostics.append(Diagnostic("coverage.evidence.invalid", "CV-n evidence must cite at least one F-n.", record.line))
        if fields.get("status") == "deferred" and fields.get("resume", "").casefold() in {"", "none", "n/a"}:
            diagnostics.append(Diagnostic("coverage.defer.resume_missing", "Deferred CV-n requires concrete resume instructions.", record.line))

    subsystems = _values(_metadata(text, "Subsystems"))
    passes = _values(_metadata(text, "Passes"))
    sweep_status = _metadata(text, "Sweep status")
    if not subsystems or not passes:
        diagnostics.append(Diagnostic("coverage.inventory.missing", "Subsystems and Passes must be non-empty comma-separated inventories."))
    if scope == "sweep":
        expected = {(subsystem, pass_name) for subsystem in subsystems for pass_name in passes}
        missing = sorted(expected - seen_pairs)
        extra = sorted(seen_pairs - expected)
        for pair in missing:
            diagnostics.append(Diagnostic("coverage.matrix.missing", f"Sweep coverage is missing {pair!r}."))
        for pair in extra:
            diagnostics.append(Diagnostic("coverage.matrix.extra", f"Sweep coverage contains uninventoried pair {pair!r}."))
        candidates = [record for record in coverage if record.fields.get("status") == "candidate"]
        if len(candidates) > int(contract["max_sweep_candidates_per_wave"]):
            diagnostics.append(Diagnostic("coverage.wave.limit", f"Sweep wave may deep-dive at most {contract['max_sweep_candidates_per_wave']} candidate surfaces."))
        deferred = [record for record in coverage if record.fields.get("status") == "deferred"]
        expected_status = "incomplete" if deferred else "complete"
        if sweep_status != expected_status:
            diagnostics.append(Diagnostic("coverage.sweep_status", f"Sweep status must be {expected_status!r} for the recorded coverage."))
        x_targets = {record.fields.get("target") for identifier, record in records.items() if identifier.startswith("X-")}
        for record in deferred:
            if record.identifier not in x_targets:
                diagnostics.append(Diagnostic("coverage.defer.unlinked", f"Deferred {record.identifier} requires an X-n limitation record.", record.line))
    elif sweep_status != "not-applicable":
        diagnostics.append(Diagnostic("coverage.targeted_status", "Targeted reports must declare '- Sweep status: not-applicable'."))
    return diagnostics


def _parse_gates(value: str) -> dict[str, str]:
    gates: dict[str, str] = {}
    for item in _values(value):
        if "=" in item:
            name, result = item.split("=", 1)
            gates[name.strip()] = result.strip()
    return gates


def _validate_research(text: str) -> list[Diagnostic]:
    records = _records(text)
    diagnostics: list[Diagnostic] = []
    for identifier, record in records.items():
        if not identifier.startswith("R-"):
            continue
        fields = record.fields
        required = {"component", "version", "source", "finding", "target", "compatibility"}
        if not required <= fields.keys():
            diagnostics.append(Diagnostic("research.fields.missing", "R-n is missing required research fields.", record.line))
            continue
        if fields["source"] == "not-applicable":
            if fields["component"] != "not-applicable" or fields["version"] != "not-applicable":
                diagnostics.append(Diagnostic("research.not_applicable.invalid", "Not-applicable research must mark component and version not-applicable.", record.line))
        else:
            if not URL_RE.fullmatch(fields["source"]):
                diagnostics.append(Diagnostic("research.source.invalid", "R-n source must be a specific HTTPS URL.", record.line))
            if fields["version"].casefold() in {"", "unknown", "latest", "unresolved"}:
                diagnostics.append(Diagnostic("research.version.unresolved", "Ecosystem research requires a resolved compatible version.", record.line))
        if not fields["target"].startswith("B-") or fields["target"] not in records:
            diagnostics.append(Diagnostic("research.target.invalid", "R-n target must reference an existing B-n baseline.", record.line))
    return diagnostics


def _validate_baselines(text: str) -> list[Diagnostic]:
    records = _records(text)
    diagnostics: list[Diagnostic] = []
    performance_claim = re.compile(r"(?:\d+(?:\.\d+)?\s*(?:%|ms|s|seconds?|minutes?|calls?|MB|GB|req/s|ops/s))", re.IGNORECASE)
    for identifier, record in records.items():
        if not identifier.startswith("B-"):
            continue
        fields = record.fields
        required = {"workflow", "method", "command", "result", "confidence", "evidence"}
        if not required <= fields.keys():
            diagnostics.append(Diagnostic("baseline.fields.missing", "B-n is missing required baseline fields.", record.line))
            continue
        method = fields["method"]
        if method not in {"command", "static", "blocked"}:
            diagnostics.append(Diagnostic("baseline.method.invalid", "B-n method must be command, static, or blocked.", record.line))
        if fields["confidence"] not in load_contract()["ratings"]:
            diagnostics.append(Diagnostic("baseline.confidence.invalid", "B-n confidence must be high, medium, or low.", record.line))
        evidence = _values(fields["evidence"])
        if not evidence or any(item not in records or not item.startswith("F-") for item in evidence):
            diagnostics.append(Diagnostic("baseline.evidence.invalid", "B-n evidence must cite existing F-n facts.", record.line))
        if method == "command":
            if fields["command"].casefold() in {"", "none", "not-run", "unknown"}:
                diagnostics.append(Diagnostic("baseline.command.missing", "Command baseline requires the exact command.", record.line))
            if not performance_claim.search(fields["result"]):
                diagnostics.append(Diagnostic("baseline.raw_result.missing", "Command baseline must include raw values with units or counts.", record.line))
        if method == "static" and performance_claim.search(fields["result"]):
            diagnostics.append(Diagnostic("baseline.static.performance_claim", "Static evidence must not claim measured timing, throughput, size, calls, or percentages.", record.line))
        if method == "blocked" and fields["confidence"] == "high":
            diagnostics.append(Diagnostic("baseline.blocked.confidence", "Blocked measurement cannot have high confidence.", record.line))
        if re.search(r"\d+(?:\.\d+)?\s*%", fields["result"]) and not re.search(
            r"\d+(?:\.\d+)?\s*(?:ms|s|seconds?|minutes?|calls?|MB|GB|req/s|ops/s)",
            fields["result"],
            re.IGNORECASE,
        ):
            diagnostics.append(Diagnostic("baseline.percentage_only", "Percentage claims require raw before/after values and units.", record.line))
    return diagnostics


def _validate_candidates(text: str, stage: str) -> list[Diagnostic]:
    contract = load_contract()
    records = _records(text)
    diagnostics: list[Diagnostic] = []
    candidates = [record for identifier, record in records.items() if identifier.startswith("C-")]
    x_targets = {record.fields.get("target") for identifier, record in records.items() if identifier.startswith("X-")}
    required_fields = {
        "band", "impact", "confidence", "effort", "risk", "verification-strength", "blast-radius",
        "reversible", "independent", "gates", "evidence", "change", "benefit", "verify", "rollback",
        "operational-cost", "experiment",
    }
    all_gates = set(contract["promotion_gates"])
    promoted: dict[str, Record] = {}
    for record in candidates:
        fields = record.fields
        if not required_fields <= fields.keys():
            diagnostics.append(Diagnostic("candidate.fields.missing", f"{record.identifier} is missing canonical candidate fields.", record.line))
            continue
        band = fields["band"]
        if band not in contract["candidate_bands"]:
            diagnostics.append(Diagnostic("candidate.band.invalid", f"{record.identifier} has an invalid band.", record.line))
            continue
        for name in ("impact", "confidence", "effort", "risk", "blast-radius"):
            if fields[name] not in contract["ratings"]:
                diagnostics.append(Diagnostic("candidate.rating.invalid", f"{record.identifier} has invalid {name}.", record.line))
        if fields["verification-strength"] not in contract["verification_strengths"]:
            diagnostics.append(Diagnostic("candidate.verification_strength.invalid", f"{record.identifier} has invalid verification strength.", record.line))
        if fields["reversible"] not in {"yes", "no"} or fields["independent"] not in {"yes", "no"}:
            diagnostics.append(Diagnostic("candidate.boolean.invalid", f"{record.identifier} reversible and independent must be yes or no.", record.line))
        gates = _parse_gates(fields["gates"])
        if set(gates) != all_gates or any(value not in {"yes", "no"} for value in gates.values()):
            diagnostics.append(Diagnostic("candidate.gates.incomplete", f"{record.identifier} must answer every promotion gate yes or no.", record.line))
            continue
        evidence = _values(fields["evidence"])
        if not any(item.startswith("F-") for item in evidence) or not any(item.startswith("B-") for item in evidence) or not any(item.startswith("R-") for item in evidence):
            diagnostics.append(Diagnostic("candidate.evidence.incomplete", f"{record.identifier} must cite F-n, B-n, and R-n evidence.", record.line))
        if any(item not in records for item in evidence):
            diagnostics.append(Diagnostic("candidate.evidence.missing", f"{record.identifier} cites missing evidence.", record.line))
        if not fields["verify"].startswith("V-") or fields["verify"] not in records:
            diagnostics.append(Diagnostic("candidate.verification.missing", f"{record.identifier} must reference an existing V-n.", record.line))
        if fields["rollback"].casefold() in {"", "none", "unknown", "n/a"}:
            diagnostics.append(Diagnostic("candidate.rollback.missing", f"{record.identifier} requires an executable rollback.", record.line))
        if fields["operational-cost"].casefold() in {"", "unknown"}:
            diagnostics.append(Diagnostic("candidate.operational_cost.missing", f"{record.identifier} requires operational-cost analysis.", record.line))

        gate_failures = {name for name, value in gates.items() if value == "no"}
        if band == "quick-win":
            if gate_failures or fields["confidence"] != "high" or fields["impact"] not in {"high", "medium"} or fields["effort"] != "low" or fields["risk"] != "low" or fields["reversible"] != "yes" or fields["independent"] != "yes" or fields["verification-strength"] != "strong":
                diagnostics.append(Diagnostic("candidate.quick_win.ineligible", f"{record.identifier} does not satisfy deterministic Quick Win gates.", record.line))
            else:
                promoted[record.identifier] = record
        elif band == "strategic-win":
            meaningful_cost = any(fields[name] != "low" for name in ("effort", "risk", "blast-radius"))
            if gate_failures or fields["impact"] != "high" or not meaningful_cost or fields["reversible"] != "yes" or fields["independent"] != "yes" or fields["verification-strength"] == "missing":
                diagnostics.append(Diagnostic("candidate.strategic_win.ineligible", f"{record.identifier} does not satisfy deterministic Strategic Win gates.", record.line))
            else:
                promoted[record.identifier] = record
        elif band == "investigate":
            if not gate_failures or not gate_failures <= {"baseline", "compatibility"} or fields["experiment"].casefold() in {"", "none", "unknown", "n/a"}:
                diagnostics.append(Diagnostic("candidate.investigate.ineligible", f"{record.identifier} must fail only baseline or compatibility gates and name a safe experiment.", record.line))
        elif band == "rejected" and record.identifier not in x_targets:
            diagnostics.append(Diagnostic("candidate.rejected.unlinked", f"Rejected {record.identifier} requires an X-n record.", record.line))

    band_rank = {name: index for index, name in enumerate(contract["candidate_bands"])}
    high_first = {"high": 0, "medium": 1, "low": 2}
    low_first = {"low": 0, "medium": 1, "high": 2}
    verification_rank = {"strong": 0, "bounded": 1, "missing": 2}

    def order_key(record: Record) -> tuple[int, int, int, int, int, int, int, int, int, int]:
        fields = record.fields
        number = int(record.identifier.split("-", 1)[1])
        return (
            band_rank.get(fields.get("band", ""), len(band_rank)),
            high_first.get(fields.get("impact", ""), 3),
            high_first.get(fields.get("confidence", ""), 3),
            verification_rank.get(fields.get("verification-strength", ""), 3),
            low_first.get(fields.get("effort", ""), 3),
            low_first.get(fields.get("risk", ""), 3),
            low_first.get(fields.get("blast-radius", ""), 3),
            0 if fields.get("reversible") == "yes" else 1,
            0 if fields.get("independent") == "yes" else 1,
            number,
        )

    expected_order = [record.identifier for record in sorted(candidates, key=order_key)]
    actual_order = [record.identifier for record in candidates]
    if actual_order != expected_order:
        diagnostics.append(Diagnostic("candidate.order.invalid", f"Candidates must follow deterministic order: {', '.join(expected_order)}."))

    verification_records = [record for identifier, record in records.items() if identifier.startswith("V-")]
    for record in verification_records:
        if not {"proves", "method", "expected"} <= record.fields.keys():
            diagnostics.append(Diagnostic("verification.fields.missing", "V-n requires proves, method, and expected fields.", record.line))
        elif record.fields["proves"] not in records or not record.fields["proves"].startswith("C-"):
            diagnostics.append(Diagnostic("verification.proves.invalid", "V-n must prove an existing C-n.", record.line))

    if stage == "implementation":
        executions = [record for identifier, record in records.items() if identifier.startswith("E-")]
        executed = {record.fields.get("candidate") for record in executions}
        if len(executed) != 1:
            diagnostics.append(Diagnostic("execution.candidate.count", "Implementation stage must execute exactly one candidate."))
        for record in executions:
            candidate_id = record.fields.get("candidate", "")
            if candidate_id not in promoted:
                diagnostics.append(Diagnostic("execution.candidate.ineligible", "E-n candidate must be an eligible Quick or Strategic Win.", record.line))
            authorization = record.fields.get("authorization", "")
            if authorization.casefold() in {"", "none", "unknown", "plan-only"}:
                diagnostics.append(Diagnostic("execution.authorization.missing", "E-n must cite explicit authorization.", record.line))
            if not {"change", "result", "regression"} <= record.fields.keys():
                diagnostics.append(Diagnostic("execution.fields.missing", "E-n requires change, result, and regression fields.", record.line))
        baselines = [record for identifier, record in records.items() if identifier.startswith("B-")]
        if len(baselines) < 2:
            diagnostics.append(Diagnostic("execution.comparison.missing", "Implementation stage requires comparable before and after B-n records."))
    return diagnostics


def validate(text: str, scope: str, stage: str, repo_root: Path) -> list[Diagnostic]:
    return [
        *_validate_shape(text, scope, stage),
        *_validate_records(text, scope, stage),
        *_validate_facts(text, repo_root),
        *_validate_coverage(text, scope),
        *_validate_baselines(text),
        *_validate_research(text),
        *_validate_candidates(text, stage),
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diagnostics = validate(read_report(args.path), args.scope, args.stage, args.repo_root)
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [item.to_dict() for item in diagnostics]}, indent=2))
    elif diagnostics:
        print("Optimization check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Optimization check passed.")
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
