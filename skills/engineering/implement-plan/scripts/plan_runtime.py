"""Canonical strict, portable runtime for plan-contract v5."""

from __future__ import annotations

import ast
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
# This table is deliberately data, rather than prose in SKILL.md.  The validator
# is the contract: an unknown field can never accidentally become a valid plan
# field simply because a planner happened to spell it plausibly.
REFERENCE_FIELDS: dict[str, dict[str, set[str]]] = {
    "D": {"evidence": {"F", "C"}},
    "CH": {"evidence": {"F"}, "directory-owner": {"CH", "F"}, "generator-owner": {"CH", "F"}},
    "P": {"owner": {"CH"}, "because": {"F"}},
    "B": {"path": {"F"}},
    "O": {"evidence": {"F"}, "decision": {"D"}, "changes": {"CH"}, "tests": {"T"}},
    "C": {"evidence": {"F"}},
    "R": {"owner": {"CH"}, "tests": {"T"}},
    "A": {"evidence": {"F"}, "resolution": {"CH", "T", "F", "D"}},
    "X": {"evidence": {"F"}},
}
FACT_FIELD_REQUIREMENTS: dict[str, set[str]] = {
    "function-signature": {"parameters", "returns"},
    "class-signature": set(),
    "schema-shape": {"fields"},
    "config-key": {"key"},
    "branch": set(),
    "error": set(),
    "side-effect": set(),
    "call-edge": {"caller", "callee"},
    "generated-from": {"generator"},
    "authorization-boundary": set(),
    "transaction-boundary": set(),
    "external-call": set(),
    "test-behavior": set(),
    "documentation-contract": set(),
}
VALID_DISPOSITIONS = {"changed", "test-only", "generated", "unchanged", "out-of-scope"}
MATERIAL_SURFACES = {
    "direct-caller", "transitive-consumer", "re-export", "fixture", "mock", "config", "schema",
    "generated-output", "generator", "documentation-contract", "deployment-hook",
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
    section: str


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
        final = self.metadata.get("final", {}) if isinstance(self.metadata, dict) else {}
        return str(final.get("tier", "")) if isinstance(final, dict) else ""

    @property
    def domains(self) -> set[str]:
        final = self.metadata.get("final", {}) if isinstance(self.metadata, dict) else {}
        domains = final.get("risk_domains", []) if isinstance(final, dict) else []
        return set(domains) if isinstance(domains, list) and all(isinstance(x, str) for x in domains) else set()

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


def _sorted_diagnostics(diagnostics: Iterable[Diagnostic]) -> list[Diagnostic]:
    """Stable public diagnostic order for deterministic repair loops."""
    return sorted(diagnostics, key=lambda item: (item.line is not None, item.line or 0, item.code, item.message))


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
            bp_section = next((name for no, name in reversed(headings) if no < n), "")
            blueprints.append(
                Blueprint(tuple(x.strip() for x in m["changes"].split(",")), m["purpose"], m["type"], body, n, bp_section)
            )
            if bp_section != "Implementation Specification":
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
        or len({x.fields.get("class") for x in plan.records.get("B", ())}) > 1
        or any(x.fields.get("surface") in {"config", "schema", "generated-output", "generator", "deployment-hook"} for x in plan.records.get("P", ()))
        or any(x.fields.get("kind") == "generated-from" for x in plan.records.get("F", ()))
        else "tiny"
    )


def snapshot(root: Path, plan: Plan | None = None) -> dict[str, Any]:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)

    inside = git("rev-parse", "--is-inside-work-tree")
    is_git = inside.returncode == 0 and inside.stdout.strip() == "true"
    dirty: dict[str, str] = {}
    tracked: dict[str, str] = {}
    untracked: dict[str, str] = {}
    if is_git:
        for raw in git("ls-files").stdout.splitlines():
            path = root / raw
            if path.is_file():
                tracked[raw.replace("\\", "/")] = _hash(path.read_bytes())
        for line in git("status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines():
            raw = line[3:].rsplit(" -> ", 1)[-1]
            path = root / raw
            digest = _hash(path.read_bytes()) if path.is_file() else "missing"
            dirty[raw.replace("\\", "/")] = digest
            if line.startswith("??"):
                untracked[raw.replace("\\", "/")] = digest
    else:
        for path in root.rglob("*"):
            if path.is_file():
                untracked[path.relative_to(root).as_posix()] = _hash(path.read_bytes())
    targets: set[str] = set()
    if plan:
        for kind in ("F", "CH"):
            for record in plan.records.get(kind, ()):
                if record.fields.get("status", "existing") == "existing":
                    targets.add(record.fields.get("path", ""))
        targets.update(r.fields.get("generator", "") for r in plan.records.get("F", ()) if r.fields.get("kind") == "generated-from")
    files = []
    for raw in sorted(targets):
        resolved = _resolve(root, raw)
        if resolved and resolved.is_file():
            files.append({"path": raw.replace("\\", "/"), "sha256": _hash(resolved.read_bytes())})
    return {
        "repository_id": (git("config", "--get", "remote.origin.url").stdout.strip() if is_git else "") or str(root.resolve()),
        "git": is_git,
        "git_head": git("rev-parse", "HEAD").stdout.strip() or None if is_git else None,
        "dirty": dirty,
        "tracked": tracked,
        "untracked": untracked,
        "files": files,
    }


def binding_for(plan: Plan, root: Path) -> dict[str, Any]:
    value = snapshot(root, plan)
    # A finalized plan is intentionally insensitive to unrelated repository
    # activity.  The planning baseline remains exhaustive; this receipt binds
    # only evidence/targets/generator sources and dirty content on those paths.
    bound_paths = {item["path"] for item in value["files"]}
    value["dirty"] = {path: digest for path, digest in value["dirty"].items() if path in bound_paths}
    value.pop("tracked", None)
    value.pop("untracked", None)
    value.pop("git_head", None)
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


def _typed_refs(ds: list[Diagnostic], record: Record, ids: set[str]) -> None:
    for field, allowed in REFERENCE_FIELDS.get(record.id.split("-", 1)[0], {}).items():
        value = record.fields.get(field, "")
        refs = _refs(value)
        if field in record.fields and not refs:
            ds.append(Diagnostic("reference.required", f"{record.id}.{field}: use at least one {', '.join(sorted(allowed))}-n reference; filler text is not valid.", record.line))
        for ref in refs:
            if ref.split("-", 1)[0] not in allowed:
                ds.append(Diagnostic("reference.type", f"{record.id}.{field} references {ref}; use only {', '.join(sorted(allowed))}-n records.", record.line))


def _concrete(value: str) -> bool:
    words = re.findall(r"[A-Za-z0-9_/-]+", value.lower())
    vague = {"works", "reliability", "necessary", "edge", "cases", "better", "cleaner", "simpler", "scalable", "done"}
    return len(words) >= 2 and not (set(words) <= vague)


def _fact_fields(ds: list[Diagnostic], fact: Record, excerpt: str, source_text: str = "") -> None:
    kind = fact.fields.get("kind", "")
    for required in FACT_FIELD_REQUIREMENTS.get(kind, set()) - set(fact.fields):
        ds.append(Diagnostic("fact.structured_required", f"{fact.id}: {kind} requires {required}.", fact.line))
    checks = {
        "parameters": fact.fields.get("parameters", ""), "returns": fact.fields.get("returns", ""),
        "fields": fact.fields.get("fields", ""), "key": fact.fields.get("key", ""),
        "caller": fact.fields.get("caller", ""), "callee": fact.fields.get("callee", ""),
        "generator": fact.fields.get("generator", ""),
    }
    for field in FACT_FIELD_REQUIREMENTS.get(kind, set()):
        value = checks[field]
        if value and field != "generator" and value not in excerpt:
            ds.append(Diagnostic("fact.structured", f"{fact.id}: claimed {field} is not present in cited source.", fact.line))
    if kind not in {"function-signature", "call-edge"} or not source_text:
        return
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return
    if kind == "function-signature":
        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        node = next((n for n in functions if n.name == fact.fields.get("anchor") and n.lineno <= int(fact.fields["lines"].split("-", 1)[1])), None)
        if node is None:
            ds.append(Diagnostic("fact.signature", f"{fact.id}: cited anchor is not a Python function in the stated range.", fact.line))
            return
        claimed = [x.strip().split(":", 1)[0].split("=", 1)[0].strip() for x in fact.fields.get("parameters", "").split(",")]
        actual = [x.arg for x in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
        if claimed != actual:
            ds.append(Diagnostic("fact.signature_parameters", f"{fact.id}: claimed parameter order does not match the Python function signature.", fact.line))
        actual_return = ast.unparse(node.returns) if node.returns is not None else "None"
        if fact.fields.get("returns", "").strip() != actual_return:
            ds.append(Diagnostic("fact.signature_returns", f"{fact.id}: claimed return annotation `{fact.fields.get('returns', '')}` does not match `{actual_return}`.", fact.line))
    else:
        callers = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fact.fields.get("caller")]
        if not callers:
            ds.append(Diagnostic("fact.call_edge", f"{fact.id}: caller `{fact.fields.get('caller')}` does not exist.", fact.line))
        elif not any(isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id == fact.fields.get("callee")) or (isinstance(n.func, ast.Attribute) and n.func.attr == fact.fields.get("callee"))) for n in ast.walk(callers[0])):
            ds.append(Diagnostic("fact.call_edge", f"{fact.id}: caller `{fact.fields.get('caller')}` does not call `{fact.fields.get('callee')}`.", fact.line))


def _metadata_diagnostics(plan: Plan) -> tuple[list[Diagnostic], dict[str, Any], dict[str, Any]]:
    """Validate untrusted metadata before any classification or set operation."""
    ds: list[Diagnostic] = []
    metadata = plan.metadata
    if not isinstance(metadata, dict):
        return [Diagnostic("metadata.shape", "Metadata must be a JSON object.")], {}, {}
    provisional, final = metadata.get("provisional"), metadata.get("final")
    if not isinstance(provisional, dict):
        ds.append(Diagnostic("metadata.provisional", "Provisional metadata must be an object."))
        provisional = {}
    if not isinstance(final, dict):
        ds.append(Diagnostic("metadata.final", "Final metadata must be an object."))
        final = {}
    for label, value in (("provisional", provisional), ("final", final)):
        intent = value.get("intent")
        if intent not in {"feature", "bug-fix", "refactor"}:
            ds.append(Diagnostic(f"metadata.{label}_intent", f"{label.title()} intent `{intent}` is unsupported; use feature, bug-fix, or refactor."))
        tier = value.get("tier")
        if tier not in TIERS:
            ds.append(Diagnostic(f"metadata.{label}_tier", f"{label.title()} tier `{tier}` is unsupported; use one of: {', '.join(TIERS)}."))
        domains = value.get("risk_domains")
        if not isinstance(domains, list) or not all(isinstance(x, str) for x in domains):
            ds.append(Diagnostic(f"metadata.{label}_domains", f"{label.title()} risk_domains must be a list of known domain strings."))
            continue
        if len(domains) != len(set(domains)):
            ds.append(Diagnostic(f"metadata.{label}_domains", f"{label.title()} risk_domains must not contain duplicates."))
        for domain in domains:
            if domain not in RISK_DOMAINS:
                ds.append(Diagnostic(f"metadata.{label}_domain", f"{label.title()} risk domain `{domain}` is unsupported."))
    return ds, provisional, final


def validate_plan(
    text: str, repo_root: Path, *, require_finalized: bool = False, baseline: dict[str, Any] | None = None
) -> tuple[Plan | None, list[Diagnostic]]:
    plan, ds = parse_plan(text)
    if not plan:
        return None, _sorted_diagnostics(ds)
    metadata_ds, provisional, final = _metadata_diagnostics(plan)
    ds.extend(metadata_ds)
    metadata_ok = not metadata_ds
    if metadata_ok and final["intent"] != provisional["intent"]:
        ds.append(Diagnostic("metadata.intent", "Final intent must match provisional intent."))
    if metadata_ok and final["tier"] in TIERS and provisional["tier"] in TIERS and TIERS.index(final["tier"]) < TIERS.index(provisional["tier"]):
        ds.append(Diagnostic("tier.downgrade", "Final tier cannot be below provisional tier."))
    if metadata_ok and plan.tier in TIERS:
        for k in REQUIRED[plan.tier]:
            if not plan.records.get(k):
                ds.append(Diagnostic("record.required", f"{plan.tier} plan requires at least one {k} record."))
    dismissed = {r.fields.get("domain") for r in plan.records.get("X", ()) if r.fields.get("status") == "dismissed"}
    if metadata_ok and not set(provisional["risk_domains"]) <= plan.domains | dismissed:
        ds.append(
            Diagnostic("domain.removal", "Provisional domains require final inclusion or a grounded X-n dismissal.")
        )
    for dismissal in plan.records.get("X", ()):
        if (
            dismissal.fields.get("domain") not in set(provisional.get("risk_domains", []))
            or dismissal.fields.get("status") != "dismissed"
            or not _refs(dismissal.fields.get("evidence", ""))
            or not _concrete(dismissal.fields.get("reason", ""))
        ):
            ds.append(Diagnostic("domain.dismissal", f"{dismissal.id}: must dismiss a provisional domain with concrete F-n evidence.", dismissal.line))
    if metadata_ok and plan.tier in TIERS and TIERS.index(plan.tier) < TIERS.index(derive_minimum_tier(plan)):
        ds.append(Diagnostic("tier.minimum", f"{derive_minimum_tier(plan)} is required by plan contents."))
    ids = plan.ids()
    for kind, rs in plan.records.items():
        for r in rs:
            _need(ds, r, kind)
            for ref in set().union(*(_refs(v) for v in r.fields.values())) - ids:
                ds.append(Diagnostic("reference.undefined", f"{r.id}: references unknown {ref}.", r.line))
            _typed_refs(ds, r, ids)
            if kind == "SC" and not all(_concrete(r.fields.get(field, "")) for field in ("given", "when", "then", "unchanged")):
                ds.append(Diagnostic("success.observable", f"{r.id}: given, when, then, and unchanged must be observable and concrete.", r.line))
            if kind == "D" and (not _concrete(r.fields.get("selected", "")) or not _concrete(r.fields.get("rejected", "")) or not _concrete(r.fields.get("drawback", ""))):
                ds.append(Diagnostic("decision.concrete", f"{r.id}: selected, rejected, and drawback must be concrete repository-grounded statements.", r.line))
            if kind == "P":
                disposition = r.fields.get("disposition")
                if disposition not in VALID_DISPOSITIONS:
                    ds.append(Diagnostic("propagation.disposition", f"{r.id}: disposition must be one of {', '.join(sorted(VALID_DISPOSITIONS))}.", r.line))
                if r.fields.get("surface") not in MATERIAL_SURFACES:
                    ds.append(Diagnostic("propagation.surface", f"{r.id}: surface must be an auditable material surface.", r.line))
                if disposition in {"changed", "test-only"} and not _refs(r.fields.get("owner", "")):
                    ds.append(Diagnostic("propagation.owner", f"{r.id}: {disposition} surface needs owning CH-n.", r.line))
                if disposition in {"unchanged", "out-of-scope"} and not _refs(r.fields.get("because", "")):
                    ds.append(Diagnostic("propagation.reason", f"{r.id}: {disposition} surface needs grounded F-n reason.", r.line))
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
        _fact_fields(ds, f, excerpt, "\n".join(source))
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
            evidence_has_anchor = False
            if evidence and p and evidence.fields.get("path", "").replace("\\", "/") == ch.fields.get("path", "").replace("\\", "/"):
                try:
                    start, end = map(int, evidence.fields.get("lines", "").split("-", 1))
                    evidence_has_anchor = ch.fields.get("anchor", "") in "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[start - 1 : end])
                except ValueError:
                    pass
            if not evidence_has_anchor:
                ds.append(
                    Diagnostic(
                        "change.evidence_anchor", f"{ch.id}: needs same-path F-n evidence whose cited range contains the exact change anchor.", ch.line
                    )
                )
        elif not p or p.exists() or not p.parent.exists() or not (ch.fields.get("directory-owner") or ch.fields.get("generator-owner")):
            ds.append(
                Diagnostic(
                    "change.new_path", f"{ch.id}: new target must be absent, contained, and have an owner.", ch.line
                )
            )
        elif ch.fields.get("generator-owner"):
            owners = _refs(ch.fields["generator-owner"])
            if not owners or not owners <= (plan.ids("F") | plan.ids("CH")):
                ds.append(Diagnostic("change.generator_owner", f"{ch.id}: generator-owner must be an F-n or CH-n authoritative generator reference.", ch.line))
        if any(
            fact.fields.get("kind") == "generated-from" and fact.fields.get("path", "") == ch.fields.get("path", "")
            for fact in facts.values()
        ) and not ch.fields.get("generator-owner"):
            ds.append(Diagnostic("change.generated_output", f"{ch.id}: generated output requires a generator owner; edit the authoritative source.", ch.line))
    expected_obligations = {d: set(OBLIGATIONS[d]) for d in plan.domains}
    seen_obligations: dict[str, set[str]] = defaultdict(set)
    for obligation_record in plan.records.get("O", ()):
        domain, obligation = obligation_record.fields.get("domain", ""), obligation_record.fields.get("obligation", "")
        if domain not in plan.domains or obligation not in OBLIGATIONS.get(domain, ()):
            ds.append(Diagnostic("obligation.domain", f"{obligation_record.id}: obligation must belong to a final risk domain.", obligation_record.line))
        if obligation in seen_obligations[domain]:
            ds.append(Diagnostic("obligation.duplicate", f"{obligation_record.id}: {domain}/{obligation} appears more than once.", obligation_record.line))
        if obligation_record.fields.get("status") != "satisfied" or not all(
            _refs(obligation_record.fields.get(field, "")) for field in ("evidence", "decision", "changes", "tests")
        ):
            ds.append(Diagnostic("obligation.format", f"{obligation_record.id}: use a concrete satisfied obligation with owned evidence, decision, changes, and tests.", obligation_record.line))
        seen_obligations[domain].add(obligation)
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
        elif not _concrete(r.fields.get("finding", "")):
            ds.append(Diagnostic("attack.finding", f"{r.id}: finding must be concrete, not a token-only placeholder.", r.line))
        elif r.fields.get("status") == "repaired" and (not _refs(r.fields.get("resolution", "")) & plan.ids("CH") or not _refs(r.fields.get("resolution", "")) & plan.ids("T")):
            ds.append(Diagnostic("attack.ownership", f"{r.id}: repaired attack needs owning CH-n and T-n resolution.", r.line))
        elif r.fields.get("status") in {"dismissed", "not-applicable"} and not _refs(r.fields.get("evidence", "")):
            ds.append(Diagnostic("attack.dismissal", f"{r.id}: dismissal needs grounded F-n evidence.", r.line))
    if plan.tier in {"standard", "high-risk"} and not plan.blueprints:
        ds.append(Diagnostic("blueprint.required", f"{plan.tier} plans require an execution blueprint."))
    for bp in plan.blueprints:
        if (
            bp.section != "Implementation Specification"
            or not bp.body
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
        domain_words = {
            "concurrency": "interleaving", "public-contract": "compatib", "migration": "interrupt",
            "security": "authorization", "external-integration": "timeout",
        }
        for domain, word in domain_words.items():
            if domain in plan.domains and word not in bp.body.lower():
                ds.append(Diagnostic("blueprint.domain", f"Blueprint must describe {domain} {word} behavior.", bp.line))
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
    if baseline is not None:
        current = snapshot(repo_root)
        if not isinstance(baseline, dict) or any(current.get(key) != baseline.get(key) for key in ("repository_id", "git", "git_head", "dirty", "tracked", "untracked")):
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
    return plan, _sorted_diagnostics(ds)


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
