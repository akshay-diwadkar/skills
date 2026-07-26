"""Canonical, portable implementation of plan-contract v5.

This file is copied verbatim into each skill that consumes plans.  It deliberately
uses only the standard library so an installed skill never needs repository imports.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

VERSION = 5
MARKER = "<!-- plan-contract: 5 -->"
RECORD_KINDS = {"SC", "F", "D", "CH", "P", "B", "O", "C", "R", "T", "A", "X"}
RISK_DOMAINS = {
    "public-contract",
    "durable-state",
    "migration",
    "security",
    "concurrency",
    "external-integration",
    "irreversible-external-effect",
}
TIERS = ("tiny", "standard", "high-risk")
HIGH_RISK = RISK_DOMAINS
REQUIRED_ATTACKS = {"forgotten-propagation", "boundary-input", "literal-implementation"}
ALLOWED_ARTIFACTS = {"pseudocode", "mermaid", "interface", "compatibility-table", "state-table", "dependency-table"}
ID_RE = re.compile(r"\b(?:SC|F|D|CH|P|B|O|C|R|T|A|X)-[1-9]\d*\b")
RECORD_RE = re.compile(
    r"^\s*-\s+(?P<id>(?:(?:SC|F|D|CH|P|B|O|C|R|T|X)-[1-9]\d*|A-(?:[1-9]\d*|[a-z][a-z-]*)))\s*:\s*(?P<body>.+?)\s*$"
)
HEADING_RE = re.compile(r"^(?P<level>#{2,4})\s+(?P<name>.+?)\s*$")
BLUEPRINT_RE = re.compile(
    r"^###\s+Execution Blueprint:\s*(?P<changes>CH-[1-9]\d*(?:\s*,\s*CH-[1-9]\d*)*)\s*—\s*(?P<purpose>.+?)\s*\[type:\s*(?P<type>[a-z-]+)\]\s*$"
)


@dataclasses.dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        where = f" on line {self.line}" if self.line else ""
        return f"Error [{self.code}]{where}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Record:
    id: str
    fields: dict[str, str]
    line: int


@dataclasses.dataclass(frozen=True)
class Fact(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Decision(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Change(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Propagation(Record):
    pass


@dataclasses.dataclass(frozen=True)
class BoundaryTrace(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Obligation(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Constraint(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Risk(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Test(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Attack(Record):
    pass


@dataclasses.dataclass(frozen=True)
class Dismissal(Record):
    pass


@dataclasses.dataclass(frozen=True)
class TraceRow:
    criterion: str
    changes: tuple[str, ...]
    tests: tuple[str, ...]
    line: int


@dataclasses.dataclass(frozen=True)
class Blueprint:
    changes: tuple[str, ...]
    purpose: str
    artifact_type: str
    body: str
    line: int


@dataclasses.dataclass(frozen=True)
class Plan:
    metadata: dict[str, Any]
    binding: dict[str, Any] | None
    receipt: dict[str, str] | None
    records: dict[str, tuple[Record, ...]]
    traceability: tuple[TraceRow, ...]
    blueprints: tuple[Blueprint, ...]
    text: str

    @property
    def tier(self) -> str:
        return str(self.metadata.get("final", {}).get("tier", ""))

    @property
    def domains(self) -> set[str]:
        return set(self.metadata.get("final", {}).get("risk_domains", []))

    def all_records(self) -> Iterable[Record]:
        for items in self.records.values():
            yield from items

    def ids(self, kind: str | None = None) -> set[str]:
        return {item.id for item in (self.records.get(kind, ()) if kind else self.all_records())}

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": VERSION,
            "metadata": self.metadata,
            "repository_binding": self.binding,
            "success_criteria": [dataclasses.asdict(x) for x in self.records.get("SC", ())],
            "facts": [dataclasses.asdict(x) for x in self.records.get("F", ())],
            "decisions": [dataclasses.asdict(x) for x in self.records.get("D", ())],
            "changes": [dataclasses.asdict(x) for x in self.records.get("CH", ())],
            "propagation": [dataclasses.asdict(x) for x in self.records.get("P", ())],
            "boundary_traces": [dataclasses.asdict(x) for x in self.records.get("B", ())],
            "obligations": [dataclasses.asdict(x) for x in self.records.get("O", ())],
            "constraints": [dataclasses.asdict(x) for x in self.records.get("C", ())],
            "risks": [dataclasses.asdict(x) for x in self.records.get("R", ())],
            "tests": [dataclasses.asdict(x) for x in self.records.get("T", ())],
            "attacks": [dataclasses.asdict(x) for x in self.records.get("A", ())],
            "dismissals": [dataclasses.asdict(x) for x in self.records.get("X", ())],
            "traceability": [dataclasses.asdict(x) for x in self.traceability],
            "blueprints": [dataclasses.asdict(x) for x in self.blueprints],
        }


def _err(code: str, record: str, why: str, repair: str, line: int | None = None) -> Diagnostic:
    return Diagnostic(code, f"{record}: {why}. {repair}", line)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text(text: str) -> str:
    return (
        "\n".join(
            x
            for x in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
            if not x.lstrip().startswith("<!-- plan-validation:")
        ).rstrip()
        + "\n"
    )


def plan_digest(text: str) -> str:
    return _hash(canonical_text(text).encode())


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def binding_digest(value: dict[str, Any]) -> str:
    return _hash(canonical_json(value).encode())


def _fields(body: str, line: int, identifier: str, diags: list[Diagnostic]) -> dict[str, str]:
    values: dict[str, str] = {}
    for piece in body.split("|"):
        if ":" not in piece:
            diags.append(
                _err(
                    "record.field",
                    identifier,
                    f"field {piece.strip()!r} is not key: value",
                    "Use pipe-delimited key: value fields",
                    line,
                )
            )
            continue
        key, value = (x.strip() for x in piece.split(":", 1))
        if not key or not value or key in values:
            diags.append(
                _err(
                    "record.field",
                    identifier,
                    "fields must be non-empty and unique",
                    "Repair the duplicate or empty field",
                    line,
                )
            )
            continue
        values[key] = value.strip("`")
    return values


def _json_marker(text: str, name: str, diags: list[Diagnostic]) -> dict[str, Any] | None:
    matches = re.findall(rf"^<!-- {re.escape(name)}: (.+) -->$", text, re.MULTILINE)
    if len(matches) != 1:
        diags.append(Diagnostic(f"{name}.count", f"Exactly one {name} marker is required."))
        return None
    try:
        value = json.loads(matches[0])
        assert isinstance(value, dict)
        return value
    except (json.JSONDecodeError, AssertionError):
        diags.append(Diagnostic(f"{name}.malformed", f"{name} must contain one JSON object."))
        return None


def parse_plan(text: str) -> tuple[Plan | None, list[Diagnostic]]:
    diags: list[Diagnostic] = []
    markers = re.findall(r"<!--\s*plan-contract:\s*(\d+)\s*-->", text)
    if len(markers) != 1 or markers[0] != "5":
        return None, [
            Diagnostic(
                "contract.unsupported",
                "Only plan-contract version 5 is supported. Regenerate the plan using the current plan-change skill.",
            )
        ]
    metadata = _json_marker(text, "plan-metadata", diags) or {}
    binding_matches = re.findall(r"^<!-- plan-repository: (.+) -->$", text, re.MULTILINE)
    binding = None
    if len(binding_matches) > 1:
        diags.append(Diagnostic("plan-repository.count", "At most one plan-repository marker is allowed."))
    elif binding_matches:
        try:
            binding = json.loads(binding_matches[0])
            if not isinstance(binding, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            diags.append(Diagnostic("plan-repository.malformed", "plan-repository must contain a JSON object."))
    receipts = re.findall(
        r"^<!-- plan-validation: 5; body-sha256: ([0-9a-f]{64}); binding-sha256: ([0-9a-f]{64}) -->$",
        text,
        re.MULTILINE,
    )
    receipt = {"body": receipts[0][0], "binding": receipts[0][1]} if len(receipts) == 1 else None
    classes: dict[str, type[Record]] = {
        "F": Fact,
        "D": Decision,
        "CH": Change,
        "P": Propagation,
        "B": BoundaryTrace,
        "O": Obligation,
        "C": Constraint,
        "R": Risk,
        "T": Test,
        "A": Attack,
        "X": Dismissal,
    }
    records: dict[str, list[Record]] = {kind: [] for kind in RECORD_KINDS}
    for no, line in enumerate(text.splitlines(), 1):
        match = RECORD_RE.match(line)
        if match:
            ident = match["id"]
            kind = ident.split("-", 1)[0]
            records[kind].append(classes.get(kind, Record)(ident, _fields(match["body"], no, ident, diags), no))
    defined = [x.id for rows in records.values() for x in rows]
    for ident, count in Counter(defined).items():
        if count > 1:
            diags.append(
                _err(
                    "reference.duplicate", ident, "record ID is defined more than once", "Give each record a unique ID"
                )
            )
    traceability: list[TraceRow] = []
    in_trace = False
    for no, line in enumerate(text.splitlines(), 1):
        if line == "## Traceability":
            in_trace = True
            continue
        if in_trace and line.startswith("## "):
            in_trace = False
        if in_trace and line.startswith("|") and "---" not in line and "Criterion" not in line:
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(cells) == 3:
                traceability.append(
                    TraceRow(
                        cells[0],
                        tuple(x.strip() for x in cells[1].split(",") if x.strip()),
                        tuple(x.strip() for x in cells[2].split(",") if x.strip()),
                        no,
                    )
                )
    blueprints: list[Blueprint] = []
    lines = text.splitlines()
    impl_start = next((i for i, x in enumerate(lines) if x == "## Implementation Specification"), -1)
    impl_end = (
        next((i for i in range(impl_start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        if impl_start >= 0
        else -1
    )
    for no, line in enumerate(lines, 1):
        m = BLUEPRINT_RE.match(line)
        if m:
            end = next(
                (i for i in range(no, len(lines)) if lines[i].startswith("### ") or lines[i].startswith("## ")),
                len(lines),
            )
            blueprints.append(
                Blueprint(
                    tuple(x.strip() for x in m["changes"].split(",")),
                    m["purpose"],
                    m["type"],
                    "\n".join(lines[no:end]).strip(),
                    no,
                )
            )
            if not (impl_start < no - 1 < impl_end):
                diags.append(
                    _err(
                        "blueprint.location",
                        "Execution Blueprint",
                        "blueprint is outside Implementation Specification",
                        "Move it under that section",
                        no,
                    )
                )
    return Plan(
        metadata,
        binding,
        receipt,
        {k: tuple(v) for k, v in records.items()},
        tuple(traceability),
        tuple(blueprints),
        text,
    ), diags


def _resolve(root: Path, raw: str) -> Path | None:
    try:
        path = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        path.relative_to(root.resolve())
        return path
    except (OSError, ValueError):
        return None


def _ids(value: str) -> set[str]:
    return set(ID_RE.findall(value))


def _refs(record: Record) -> set[str]:
    return set().union(*(_ids(v) for v in record.fields.values()))


def derive_minimum_tier(plan: Plan) -> str:
    if plan.domains & HIGH_RISK:
        return "high-risk"
    changes = plan.records.get("CH", ())
    if len({x.fields.get("path") for x in changes}) > 1 or plan.records.get("C"):
        return "standard"
    return "tiny"


def binding_for(plan: Plan, root: Path) -> dict[str, Any]:
    files: set[str] = set()
    for kind in ("F", "CH"):
        for record in plan.records.get(kind, ()):
            if record.fields.get("status", "existing") == "existing" and record.fields.get("path"):
                files.add(record.fields["path"])
    entries = []
    for raw in sorted(files):
        path = _resolve(root, raw)
        if path and path.is_file():
            entries.append({"path": raw.replace("\\", "/"), "sha256": _hash(path.read_bytes())})

    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    status = git("status", "--porcelain=v1", "--untracked-files=all")
    unbound_body = (
        "\n".join(
            line for line in canonical_text(plan.text).splitlines() if not line.startswith("<!-- plan-repository:")
        )
        + "\n"
    )
    return {
        "repository_id": git("config", "--get", "remote.origin.url") or str(root.resolve()),
        "git_head": git("rev-parse", "HEAD") or None,
        "dirty": status.splitlines(),
        "files": entries,
        "plan_body_sha256": _hash(unbound_body.encode()),
    }


def validate_plan(
    text: str, repo_root: Path, *, require_finalized: bool = False
) -> tuple[Plan | None, list[Diagnostic]]:
    plan, diags = parse_plan(text)
    if plan is None:
        return None, diags
    final = plan.metadata.get("final")
    provisional = plan.metadata.get("provisional")
    if not isinstance(final, dict) or not isinstance(provisional, dict):
        diags.append(Diagnostic("metadata.shape", "Metadata needs provisional and final objects."))
        return plan, diags
    tier = plan.tier
    domains = plan.domains
    if tier not in TIERS or not domains <= RISK_DOMAINS or len(domains) != len(final.get("risk_domains", [])):
        diags.append(Diagnostic("metadata.classification", "Final tier and unique risk domains must be valid."))
    if TIERS.index(tier) < TIERS.index(str(provisional.get("tier", ""))):
        diags.append(Diagnostic("tier.downgrade", "Final tier cannot be below provisional tier."))
    dismissed = {x.fields.get("domain") for x in plan.records.get("X", ()) if x.fields.get("status") == "dismissed"}
    if not set(provisional.get("risk_domains", [])) <= domains | dismissed:
        diags.append(
            Diagnostic("domain.removal", "Provisional domains require final inclusion or a grounded X-n dismissal.")
        )
    minimum = derive_minimum_tier(plan)
    if tier in TIERS and TIERS.index(tier) < TIERS.index(minimum):
        diags.append(Diagnostic("tier.minimum", f"{minimum} is required by plan records."))
    known = plan.ids()
    for record in plan.all_records():
        for ref in _refs(record) - known:
            diags.append(
                _err(
                    "reference.undefined",
                    record.id,
                    f"references unknown {ref}",
                    "Add the record or repair the reference",
                    record.line,
                )
            )
    for fact in plan.records.get("F", ()):
        fields = fact.fields
        path = _resolve(repo_root, fields.get("path", ""))
        for required in ("kind", "path", "lines", "anchor", "excerpt-sha256", "file-sha256", "observation"):
            if required not in fields:
                diags.append(
                    _err("fact.field", fact.id, f"missing {required}", "Supply the typed fact field", fact.line)
                )
        if not path or not path.is_file():
            diags.append(
                _err(
                    "fact.path",
                    fact.id,
                    "path is missing, outside the repository, or absent",
                    "Cite an in-repository file",
                    fact.line,
                )
            )
            continue
        try:
            start, end = (int(x) for x in fields.get("lines", "-").split("-", 1))
            source = path.read_text(encoding="utf-8", errors="replace").splitlines()
            excerpt = "\n".join(source[start - 1 : end]) + "\n"
        except ValueError:
            diags.append(
                _err("fact.lines", fact.id, "lines must be start-end", "Use a valid inclusive range", fact.line)
            )
            continue
        if start < 1 or end < start or end > len(source):
            diags.append(
                _err("fact.lines", fact.id, "line range is outside the file", "Use a current range", fact.line)
            )
        elif fields.get("anchor", "") not in "\n".join(source[start - 1 : end]):
            diags.append(
                _err(
                    "fact.anchor",
                    fact.id,
                    "anchor is absent from cited range",
                    "Cite the range containing the anchor",
                    fact.line,
                )
            )
        if fields.get("file-sha256") not in {None, _hash(path.read_bytes())}:
            diags.append(_err("fact.stale", fact.id, "file fingerprint is stale", "Refresh the fact", fact.line))
        if fields.get("excerpt-sha256") not in {None, _hash(excerpt.encode())}:
            diags.append(
                _err("fact.excerpt", fact.id, "excerpt fingerprint is stale", "Refresh the cited excerpt", fact.line)
            )
    facts = {x.id: x for x in plan.records.get("F", ())}
    for change in plan.records.get("CH", ()):
        f = change.fields
        path = _resolve(repo_root, f.get("path", ""))
        evidence = f.get("evidence", "")
        if f.get("status") not in {"existing", "new"}:
            diags.append(
                _err("change.status", change.id, "status must be existing or new", "Set status explicitly", change.line)
            )
        if f.get("status") == "existing":
            if not path or not path.is_file():
                diags.append(
                    _err(
                        "change.target",
                        change.id,
                        "existing target is absent or escapes repository",
                        "Use a current target",
                        change.line,
                    )
                )
            elif f.get("anchor", "") not in path.read_text(encoding="utf-8", errors="replace"):
                diags.append(
                    _err("change.anchor", change.id, "anchor is absent", "Use the current target anchor", change.line)
                )
            evidence_fact = facts.get(evidence)
            if not evidence_fact or evidence_fact.fields.get("path", "").replace("\\", "/") != f.get(
                "path", ""
            ).replace("\\", "/"):
                diags.append(
                    _err(
                        "change.evidence_path_mismatch",
                        change.id,
                        f"changes `{f.get('path')}`, but {evidence or 'no evidence'} does not cite it",
                        "Add a same-path F-n and reference it",
                        change.line,
                    )
                )
    for row in plan.traceability:
        if (
            row.criterion not in plan.ids("SC") | plan.ids("C")
            or not set(row.changes) <= plan.ids("CH")
            or not set(row.tests) <= plan.ids("T")
        ):
            diags.append(
                _err(
                    "traceability.reference",
                    row.criterion,
                    "row contains an unknown or wrong-type ID",
                    "Use SC/C, CH, and T IDs",
                    row.line,
                )
            )
    traced_c = {x.criterion for x in plan.traceability}
    traced_ch = set().union(*(set(x.changes) for x in plan.traceability), set())
    traced_t = set().union(*(set(x.tests) for x in plan.traceability), set())
    for ident in (plan.ids("SC") | plan.ids("C")) - traced_c:
        diags.append(Diagnostic("traceability.criterion", f"{ident} needs an exact traceability row."))
    for ident in plan.ids("CH") - traced_ch:
        diags.append(Diagnostic("traceability.change", f"{ident} is not mapped in traceability."))
    for ident in plan.ids("T") - traced_t:
        diags.append(Diagnostic("traceability.test", f"{ident} is not mapped in traceability."))
    if tier in {"standard", "high-risk"} and not plan.blueprints:
        diags.append(Diagnostic("blueprint.required", f"{tier} plans require an execution blueprint."))
    for bp in plan.blueprints:
        if not bp.body or bp.artifact_type not in ALLOWED_ARTIFACTS or not set(bp.changes) <= plan.ids("CH"):
            diags.append(
                _err(
                    "blueprint.invalid",
                    "Execution Blueprint",
                    "artifact or CH reference is invalid",
                    "Use an allowed type and existing CH-n",
                    bp.line,
                )
            )
    attacks = {x.id.removeprefix("A-"): x for x in plan.records.get("A", ())}
    for name in REQUIRED_ATTACKS - attacks.keys():
        diags.append(Diagnostic("attack.required", f"A-{name} is required."))
    for attack in attacks.values():
        if (
            attack.fields.get("status") not in {"repaired", "dismissed", "not-applicable"}
            or not attack.fields.get("evidence")
            or not attack.fields.get("resolution")
        ):
            diags.append(
                _err(
                    "attack.format",
                    attack.id,
                    "requires status, finding, evidence, and resolution",
                    "Use the strict attack record",
                    attack.line,
                )
            )
    if require_finalized:
        if not plan.receipt or not plan.binding:
            diags.append(Diagnostic("receipt.missing", "Finalized v5 plan needs repository binding and receipt."))
        elif plan.receipt["body"] != plan_digest(text) or plan.receipt["binding"] != binding_digest(plan.binding):
            diags.append(Diagnostic("receipt.stale", "Plan receipt does not match plan body or binding."))
        elif binding_for(plan, repo_root) != plan.binding:
            diags.append(Diagnostic("binding.stale", "A bound evidence or change target changed; regenerate the plan."))
    return plan, diags


def finalized_text(text: str, root: Path) -> str:
    plan, diags = validate_plan(text, root)
    if plan is None or diags:
        raise ValueError("\n".join(str(x) for x in diags))
    binding = binding_for(plan, root)
    lines = [x for x in canonical_text(text).splitlines() if not x.startswith("<!-- plan-repository:")]
    at = next((i + 1 for i, x in enumerate(lines) if x == MARKER), 1)
    lines.insert(at, "<!-- plan-repository: " + canonical_json(binding) + " -->")
    body = "\n".join(lines) + "\n"
    lines.insert(
        at + 1,
        f"<!-- plan-validation: 5; body-sha256: {plan_digest(body)}; binding-sha256: {binding_digest(binding)} -->",
    )
    return "\n".join(lines) + "\n"
