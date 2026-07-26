"""Canonical strict, portable runtime for plan-contract v5."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

VERSION = 5
MARKER = "<!-- plan-contract: 5 -->"
TIERS = ("tiny", "standard", "high-risk")
RISK_DOMAINS = {
    "public-contract",
    "durable-state",
    "migration",
    "security",
    "concurrency",
    "external-integration",
    "irreversible-external-effect",
}
SECTIONS = (
    "Outcome and Scope",
    "Evidence Ledger",
    "Decisions",
    "Implementation Specification",
    "Propagation Record",
    "Boundary Traces",
    "Domain Obligations",
    "Traceability",
    "Verification",
    "Risks, Assumptions, and Attack",
)
SCHEMA: dict[str, tuple[set[str], set[str], str]] = {
    "SC": ({"given", "when", "then", "unchanged"}, set(), "Outcome and Scope"),
    "F": (
        {"kind", "path", "lines", "anchor", "excerpt-sha256", "file-sha256", "observation"},
        {"parameters", "returns", "fields", "key", "caller", "callee", "generator"},
        "Evidence Ledger",
    ),
    "D": ({"selected", "evidence", "rejected", "drawback"}, set(), "Decisions"),
    "CH": (
        {"path", "anchor", "status", "evidence", "change"},
        {"directory-owner", "generator-owner"},
        "Implementation Specification",
    ),
    "P": ({"owner", "because", "surface", "disposition"}, set(), "Propagation Record"),
    "B": ({"class", "path", "flow"}, set(), "Boundary Traces"),
    "O": ({"domain", "obligation", "status", "evidence", "decision", "changes", "tests"}, set(), "Domain Obligations"),
    "C": ({"constraint"}, {"evidence"}, "Decisions"),
    "R": ({"severity", "owner", "tests", "risk"}, set(), "Risks, Assumptions, and Attack"),
    "T": ({"given", "when", "then", "command"}, set(), "Verification"),
    "A": ({"status", "finding", "evidence", "resolution"}, set(), "Risks, Assumptions, and Attack"),
    "X": ({"domain", "status", "evidence", "reason"}, set(), "Risks, Assumptions, and Attack"),
}
REQUIRED = {
    "tiny": {"SC", "F", "D", "CH", "P", "B", "T", "A"},
    "standard": {"SC", "F", "D", "CH", "P", "B", "C", "T", "A"},
    "high-risk": {"SC", "F", "D", "CH", "P", "B", "C", "R", "T", "A", "O"},
}
REQUIRED_ATTACKS = {"forgotten-propagation", "boundary-input", "literal-implementation"}
DOMAIN_ATTACKS = {
    "security": {"security", "authorization-bypass"},
    "concurrency": {"concurrency"},
    "public-contract": {"compatibility"},
    "migration": {"migration-interruption", "rollback"},
    "external-integration": {"ambiguous-success"},
    "irreversible-external-effect": {"ambiguous-success", "rollback"},
}
OBLIGATIONS = {
    "security": (
        "principal",
        "tenant",
        "trust-boundary",
        "authorization-owner",
        "validation-order",
        "denial-semantics",
        "enumeration-resistance",
        "revocation",
        "audit-behavior",
        "cross-tenant-tests",
    ),
    "concurrency": (
        "shared-state",
        "transaction-or-lock-boundary",
        "idempotency-identity",
        "retries",
        "duplicate-delivery",
        "cancellation",
        "ordering",
        "worst-interleaving",
        "reconciliation",
    ),
    "public-contract": (
        "current-shape",
        "proposed-shape",
        "defaults-and-nullability",
        "errors",
        "old-writer-new-reader",
        "new-writer-old-reader",
        "generated-clients",
        "mixed-version-rollout",
        "compatibility-tests",
    ),
    "durable-state": (
        "current-state",
        "target-state",
        "forward-migration",
        "backward-compatibility",
        "partial-migration",
        "interrupted-migration",
        "rollback-or-roll-forward",
        "queue-cache-index-effects",
        "data-verification",
        "deployment-order",
    ),
    "migration": (
        "current-state",
        "target-state",
        "forward-migration",
        "backward-compatibility",
        "partial-migration",
        "interrupted-migration",
        "rollback-or-roll-forward",
        "queue-cache-index-effects",
        "data-verification",
        "deployment-order",
    ),
    "external-integration": (
        "sdk-or-api-version",
        "authentication",
        "timeout",
        "retryable-errors",
        "non-retryable-errors",
        "rate-limits",
        "idempotency",
        "malformed-responses",
        "ambiguous-success",
        "reconciliation",
        "irreversible-effects",
    ),
    "irreversible-external-effect": (
        "sdk-or-api-version",
        "authentication",
        "timeout",
        "retryable-errors",
        "non-retryable-errors",
        "rate-limits",
        "idempotency",
        "malformed-responses",
        "ambiguous-success",
        "reconciliation",
        "irreversible-effects",
    ),
}
FACT_KINDS = {
    "function-signature",
    "class-signature",
    "schema-shape",
    "config-key",
    "branch",
    "error",
    "side-effect",
    "call-edge",
    "generated-from",
    "authorization-boundary",
    "transaction-boundary",
    "external-call",
    "test-behavior",
    "documentation-contract",
}
ID = re.compile(r"\b(?:SC|F|D|CH|P|B|O|C|R|T|X)-[1-9]\d*\b")
REC = re.compile(
    r"^\s*-\s+(?P<id>(?:SC|F|D|CH|P|B|O|C|R|T|X)-[1-9]\d*|A-(?:[1-9]\d*|[a-z][a-z-]*))\s*:\s*(?P<body>.+)$"
)
BP = re.compile(
    r"^### Execution Blueprint: (?P<changes>CH-[1-9]\d*(?:,\s*CH-[1-9]\d*)*) — (?P<purpose>.+) \[type: (?P<type>[a-z-]+)\]$"
)


@dataclasses.dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        return f"Error [{self.code}]" + (f" on line {self.line}" if self.line else "") + f": {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Record:
    id: str
    fields: dict[str, str]
    line: int
    section: str


@dataclasses.dataclass(frozen=True)
class Blueprint:
    changes: tuple[str, ...]
    purpose: str
    artifact_type: str
    body: str
    line: int


@dataclasses.dataclass(frozen=True)
class TraceRow:
    criterion: str
    changes: tuple[str, ...]
    tests: tuple[str, ...]
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
        return (r for rs in self.records.values() for r in rs)

    def ids(self, kind: str | None = None) -> set[str]:
        return {r.id for r in (self.records.get(kind, ()) if kind else self.all_records())}

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": VERSION,
            "metadata": self.metadata,
            "repository_binding": self.binding,
            "records": {k: [dataclasses.asdict(x) for x in v] for k, v in self.records.items()},
            "traceability": [dataclasses.asdict(x) for x in self.traceability],
            "blueprints": [dataclasses.asdict(x) for x in self.blueprints],
        }


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text(text: str) -> str:
    return (
        "\n".join(
            x for x in text.replace("\r\n", "\n").splitlines() if not x.startswith("<!-- plan-validation:")
        ).rstrip()
        + "\n"
    )


def plan_digest(text: str) -> str:
    return _hash(canonical_text(text).encode())


def _json(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def binding_digest(v: dict[str, Any]) -> str:
    return _hash(_json(v).encode())


def _refs(v: str) -> set[str]:
    return set(ID.findall(v))


def _resolve(root: Path, raw: str) -> Path | None:
    try:
        if not raw or ".." in Path(raw).parts:
            return None
        p = (root / raw).resolve()
        p.relative_to(root.resolve())
        return p
    except (OSError, ValueError):
        return None


def _fields(body: str, ident: str, line: int, ds: list[Diagnostic]) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split("|"):
        if ":" not in part:
            ds.append(Diagnostic("record.field", f"{ident}: fields must be key: value.", line))
            continue
        k, v = (x.strip() for x in part.split(":", 1))
        if not k or not v or k in out:
            ds.append(Diagnostic("record.field", f"{ident}: fields must be non-empty and unique.", line))
            continue
        out[k] = v.strip("`")
    return out


def _marker(text: str, name: str, ds: list[Diagnostic]) -> dict[str, Any] | None:
    values = re.findall(rf"^<!-- {re.escape(name)}: (.+) -->$", text, re.M)
    if len(values) != 1:
        ds.append(Diagnostic(f"{name}.count", f"Exactly one {name} marker is required."))
        return None
    try:
        value = json.loads(values[0])
        assert isinstance(value, dict)
        return value
    except (json.JSONDecodeError, AssertionError):
        ds.append(Diagnostic(f"{name}.malformed", f"{name} must be a JSON object."))
        return None


def parse_plan(text: str) -> tuple[Plan | None, list[Diagnostic]]:
    if re.findall(r"<!--\s*plan-contract:\s*(\d+)\s*-->", text) != ["5"]:
        return None, [
            Diagnostic(
                "contract.unsupported",
                "Only plan-contract version 5 is supported. Regenerate the plan using the current plan-change skill.",
            )
        ]
    ds: list[Diagnostic] = []
    meta = _marker(text, "plan-metadata", ds) or {}
    bind = _marker(text, "plan-repository", ds) if "<!-- plan-repository:" in text else None
    receipt_matches = re.findall(
        r"^<!-- plan-validation: 5; body-sha256: ([0-9a-f]{64}); binding-sha256: ([0-9a-f]{64}) -->$", text, re.M
    )
    receipt = {"body": receipt_matches[0][0], "binding": receipt_matches[0][1]} if len(receipt_matches) == 1 else None
    headings = [(i + 1, x[3:]) for i, x in enumerate(text.splitlines()) if x.startswith("## ")]
    names = [x[1] for x in headings]
    if names != list(SECTIONS):
        ds.append(Diagnostic("section.order", "Canonical sections must occur exactly once in the required order."))
    section = ""
    records: dict[str, list[Record]] = defaultdict(list)
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:]
        m = REC.match(line)
        if m:
            ident = m["id"]
            kind = ident.split("-", 1)[0]
            records[kind].append(Record(ident, _fields(m["body"], ident, n, ds), n, section))
    for ident, count in Counter(r.id for rs in records.values() for r in rs).items():
        if count > 1:
            ds.append(Diagnostic("reference.duplicate", f"{ident}: record ID is defined more than once."))
    traces: list[TraceRow] = []
    trace = False
    for n, line in enumerate(lines, 1):
        if line == "## Traceability":
            trace = True
            continue
        if trace and line.startswith("## "):
            trace = False
        if trace and line.startswith("|") and "---" not in line and "Criterion" not in line:
            c = [x.strip() for x in line.strip("|").split("|")]
            if len(c) == 3:
                traces.append(
                    TraceRow(
                        c[0],
                        tuple(x.strip() for x in c[1].split(",") if x.strip()),
                        tuple(x.strip() for x in c[2].split(",") if x.strip()),
                        n,
                    )
                )
            else:
                ds.append(
                    Diagnostic("traceability.shape", "Traceability rows require criterion, changes, and tests.", n)
                )
    blueprints: list[Blueprint] = []
    for n, line in enumerate(lines, 1):
        m = BP.match(line)
        if m:
            end = next(
                (i for i in range(n, len(lines)) if lines[i].startswith("### ") or lines[i].startswith("## ")),
                len(lines),
            )
            body = "\n".join(lines[n:end]).strip()
            blueprints.append(
                Blueprint(tuple(x.strip() for x in m["changes"].split(",")), m["purpose"], m["type"], body, n)
            )
            if not any(no < n and name == "Implementation Specification" for no, name in headings) or next(
                (name for no, name in headings if no > n), ""
            ) not in {"Propagation Record"}:
                ds.append(
                    Diagnostic(
                        "blueprint.location", "Execution Blueprint must be inside Implementation Specification.", n
                    )
                )
    return Plan(
        meta, bind, receipt, {k: tuple(v) for k, v in records.items()}, tuple(traces), tuple(blueprints), text
    ), ds


def derive_minimum_tier(plan: Plan) -> str:
    if plan.domains:
        return "high-risk"
    changes = plan.records.get("CH", ())
    return (
        "standard"
        if len({x.fields.get("path") for x in changes}) > 1
        or plan.records.get("C")
        or any(x.fields.get("surface") in {"config", "schema", "generated-output"} for x in plan.records.get("P", ()))
        else "tiny"
    )


def snapshot(root: Path, plan: Plan | None = None) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False).stdout.strip()

    status = git("status", "--porcelain=v1", "--untracked-files=all")
    dirty = {}
    for line in status.splitlines():
        raw = line[3:]
        dirty_path = root / raw
        dirty[raw.replace("\\", "/")] = _hash(dirty_path.read_bytes()) if dirty_path.is_file() else "missing"
    targets = set()
    if plan:
        for kind in ("F", "CH"):
            for r in plan.records.get(kind, ()):
                if r.fields.get("status", "existing") == "existing":
                    targets.add(r.fields.get("path", ""))
    files = [
        {"path": raw.replace("\\", "/"), "sha256": _hash(resolved_path.read_bytes())}
        for raw in sorted(targets)
        if (resolved_path := _resolve(root, raw)) is not None and resolved_path.is_file()
    ]
    return {
        "repository_id": git("config", "--get", "remote.origin.url") or str(root.resolve()),
        "git_head": git("rev-parse", "HEAD") or None,
        "dirty": dirty,
        "files": files,
    }


def binding_for(plan: Plan, root: Path) -> dict[str, Any]:
    value = snapshot(root, plan)
    value["plan_body_sha256"] = _hash(
        "\n".join(
            x for x in canonical_text(plan.text).splitlines() if not x.startswith("<!-- plan-repository:")
        ).encode()
    )
    return value


def _need(ds: list[Diagnostic], r: Record, kind: str) -> None:
    required, optional, section = SCHEMA[kind]
    if r.section != section:
        ds.append(Diagnostic("record.section", f"{r.id}: must occur in {section}.", r.line))
    for field in required - set(r.fields):
        ds.append(Diagnostic("record.required", f"{r.id}: missing {field}.", r.line))
    for field in set(r.fields) - required - optional:
        ds.append(Diagnostic("record.unknown_field", f"{r.id}: unsupported field {field}.", r.line))


def validate_plan(
    text: str, repo_root: Path, *, require_finalized: bool = False, baseline: dict[str, Any] | None = None
) -> tuple[Plan | None, list[Diagnostic]]:
    plan, ds = parse_plan(text)
    if not plan:
        return None, ds
    final, provisional = plan.metadata.get("final"), plan.metadata.get("provisional")
    if not isinstance(final, dict) or not isinstance(provisional, dict):
        return plan, ds + [Diagnostic("metadata.shape", "Metadata needs provisional and final objects.")]
    if plan.tier not in TIERS or not plan.domains <= RISK_DOMAINS:
        ds.append(Diagnostic("metadata.classification", "Final tier and risk domains are invalid."))
    if plan.tier in TIERS:
        for k in REQUIRED[plan.tier]:
            if not plan.records.get(k):
                ds.append(Diagnostic("record.required", f"{plan.tier} plan requires at least one {k} record."))
    if TIERS.index(plan.tier) < TIERS.index(str(provisional.get("tier", "tiny"))):
        ds.append(Diagnostic("tier.downgrade", "Final tier cannot be below provisional tier."))
    dismissed = {r.fields.get("domain") for r in plan.records.get("X", ()) if r.fields.get("status") == "dismissed"}
    if not set(provisional.get("risk_domains", [])) <= plan.domains | dismissed:
        ds.append(
            Diagnostic("domain.removal", "Provisional domains require final inclusion or a grounded X-n dismissal.")
        )
    if plan.tier in TIERS and TIERS.index(plan.tier) < TIERS.index(derive_minimum_tier(plan)):
        ds.append(Diagnostic("tier.minimum", f"{derive_minimum_tier(plan)} is required by plan contents."))
    ids = plan.ids()
    for kind, rs in plan.records.items():
        for r in rs:
            _need(ds, r, kind)
            for ref in set().union(*(_refs(v) for v in r.fields.values())) - ids:
                ds.append(Diagnostic("reference.undefined", f"{r.id}: references unknown {ref}.", r.line))
    facts = {r.id: r for r in plan.records.get("F", ())}
    for f in facts.values():
        if f.fields.get("kind") not in FACT_KINDS:
            ds.append(Diagnostic("fact.kind", f"{f.id}: unsupported fact kind.", f.line))
            continue
        path = _resolve(repo_root, f.fields.get("path", ""))
        if not path or not path.is_file():
            ds.append(Diagnostic("fact.path", f"{f.id}: path is missing, outside the repository, or absent.", f.line))
            continue
        try:
            start, end = map(int, f.fields["lines"].split("-", 1))
            source = path.read_text(encoding="utf-8", errors="replace").splitlines()
            excerpt = "\n".join(source[start - 1 : end]) + "\n"
        except (KeyError, ValueError):
            ds.append(Diagnostic("fact.lines", f"{f.id}: lines must be a valid inclusive range.", f.line))
            continue
        fact_anchor = f.fields.get("anchor", "")
        if start < 1 or end < start or end > len(source) or fact_anchor not in excerpt:
            ds.append(Diagnostic("fact.anchor", f"{f.id}: anchor must occur in the cited range.", f.line))
        if f.fields.get("file-sha256") != _hash(path.read_bytes()) or f.fields.get("excerpt-sha256") != _hash(
            excerpt.encode()
        ):
            ds.append(Diagnostic("fact.stale", f"{f.id}: fact fingerprints are stale.", f.line))
        if (
            f.fields["kind"] == "function-signature"
            and f.fields.get("parameters")
            and f.fields["parameters"] not in excerpt
        ):
            ds.append(Diagnostic("fact.structured", f"{f.id}: claimed parameters are not in cited signature.", f.line))
    for ch in plan.records.get("CH", ()):
        p = _resolve(repo_root, ch.fields.get("path", ""))
        status = ch.fields.get("status")
        if status not in {"existing", "new"}:
            ds.append(Diagnostic("change.status", f"{ch.id}: status must be existing or new.", ch.line))
            continue
        if status == "existing":
            evidence = facts.get(ch.fields.get("evidence", ""))
            if not p or not p.is_file():
                ds.append(Diagnostic("change.target", f"{ch.id}: existing target is absent or unsafe.", ch.line))
            elif ch.fields.get("anchor", "") not in p.read_text(encoding="utf-8", errors="replace"):
                ds.append(Diagnostic("change.anchor", f"{ch.id}: anchor is absent.", ch.line))
            if (
                not evidence
                or evidence.fields.get("path", "").replace("\\", "/") != ch.fields.get("path", "").replace("\\", "/")
                or ch.fields.get("anchor", "") not in evidence.fields.get("anchor", "")
            ):
                ds.append(
                    Diagnostic(
                        "change.evidence_anchor", f"{ch.id}: needs same-path, same-anchor F-n evidence.", ch.line
                    )
                )
        elif (
            not p
            or p.exists()
            or not p.parent.exists()
            or not (ch.fields.get("directory-owner") or ch.fields.get("generator-owner"))
        ):
            ds.append(
                Diagnostic(
                    "change.new_path", f"{ch.id}: new target must be absent, contained, and have an owner.", ch.line
                )
            )
    expected_obligations = {d: set(OBLIGATIONS[d]) for d in plan.domains}
    seen_obligations: dict[str, set[str]] = defaultdict(set)
    for obligation_record in plan.records.get("O", ()):
        seen_obligations[obligation_record.fields.get("domain", "")].add(obligation_record.fields.get("obligation", ""))
    for d, needed in expected_obligations.items():
        for obligation_name in needed - seen_obligations[d]:
            ds.append(Diagnostic("obligation.required", f"{d}: missing obligation {obligation_name}."))
    attacks = {r.id[2:]: r for r in plan.records.get("A", ())}
    needed_attacks = REQUIRED_ATTACKS | set().union(*(DOMAIN_ATTACKS.get(d, set()) for d in plan.domains))
    for attack_name in needed_attacks - attacks.keys():
        ds.append(Diagnostic("attack.required", f"A-{attack_name} is required."))
    for r in attacks.values():
        if (
            r.fields.get("status") not in {"repaired", "dismissed", "not-applicable"}
            or not r.fields.get("finding")
            or not r.fields.get("evidence")
            or not r.fields.get("resolution")
        ):
            ds.append(
                Diagnostic(
                    "attack.format", f"{r.id}: requires concrete status, finding, evidence, and resolution.", r.line
                )
            )
    if plan.tier in {"standard", "high-risk"} and not plan.blueprints:
        ds.append(Diagnostic("blueprint.required", f"{plan.tier} plans require an execution blueprint."))
    for bp in plan.blueprints:
        if (
            not bp.body
            or not bp.purpose
            or bp.artifact_type
            not in {"pseudocode", "mermaid", "interface", "compatibility-table", "state-table", "dependency-table"}
            or not set(bp.changes) <= plan.ids("CH")
        ):
            ds.append(
                Diagnostic(
                    "blueprint.invalid",
                    "Blueprint must be non-empty, allowed, purposeful, and own existing changes.",
                    bp.line,
                )
            )
    traced = {r.criterion for r in plan.traceability}
    chs = set().union(*(set(r.changes) for r in plan.traceability), set())
    tests = set().union(*(set(r.tests) for r in plan.traceability), set())
    for row in plan.traceability:
        if (
            row.criterion not in plan.ids("SC") | plan.ids("C")
            or not row.changes
            or not row.tests
            or not set(row.changes) <= plan.ids("CH")
            or not set(row.tests) <= plan.ids("T")
        ):
            ds.append(
                Diagnostic(
                    "traceability.reference",
                    "Traceability must use exact SC/C, CH, and T IDs with non-empty cells.",
                    row.line,
                )
            )
    for ident in (plan.ids("SC") | plan.ids("C")) - traced:
        ds.append(Diagnostic("traceability.criterion", f"{ident} needs an exact traceability row."))
    for ident in plan.ids("CH") - chs:
        ds.append(Diagnostic("traceability.change", f"{ident} is not mapped in traceability."))
    for ident in plan.ids("T") - tests:
        ds.append(Diagnostic("traceability.test", f"{ident} is not mapped in traceability."))
    if baseline is not None and snapshot(repo_root, plan).get("dirty") != baseline.get("dirty"):
        ds.append(Diagnostic("snapshot.mutation", "Planner changed the target repository after its baseline snapshot."))
    if require_finalized:
        if not plan.receipt or not plan.binding:
            ds.append(Diagnostic("receipt.missing", "Finalized v5 plan needs repository binding and receipt."))
        elif plan.receipt["body"] != plan_digest(text) or plan.receipt["binding"] != binding_digest(plan.binding):
            ds.append(Diagnostic("receipt.stale", "Plan receipt does not match plan body or binding."))
        elif binding_for(plan, repo_root) != plan.binding:
            ds.append(
                Diagnostic("binding.stale", "A bound evidence, target, or baseline changed; regenerate the plan.")
            )
    return plan, ds


def finalized_text(text: str, root: Path, baseline: dict[str, Any] | None = None) -> str:
    plan, ds = validate_plan(text, root, baseline=baseline)
    if not plan or ds:
        raise ValueError("\n".join(str(x) for x in ds))
    binding = binding_for(plan, root)
    lines = [x for x in canonical_text(text).splitlines() if not x.startswith("<!-- plan-repository:")]
    at = lines.index(MARKER) + 1
    lines.insert(at, "<!-- plan-repository: " + _json(binding) + " -->")
    body = "\n".join(lines) + "\n"
    lines.insert(
        at + 1,
        f"<!-- plan-validation: 5; body-sha256: {plan_digest(body)}; binding-sha256: {binding_digest(binding)} -->",
    )
    return "\n".join(lines) + "\n"
