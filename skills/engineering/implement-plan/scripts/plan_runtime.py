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

from plan_contract_data import CONTRACT

VERSION = int(CONTRACT["contract_version"])
MARKER = str(CONTRACT["marker"])
TIERS = tuple(str(value) for value in CONTRACT["tiers"])
RISK_DOMAINS = {str(value) for value in CONTRACT["risk_domains"]}
SECTIONS = tuple(str(value) for value in CONTRACT["sections"])
SCHEMA: dict[str, tuple[set[str], set[str], str]] = {
    kind: (set(value["required"]), set(value["optional"]), str(value["section"]))
    for kind, value in CONTRACT["record_schemas"].items()
}
REFERENCE_FIELDS: dict[str, dict[str, set[str]]] = {
    kind: {field: set(allowed) for field, allowed in fields.items()}
    for kind, fields in CONTRACT["reference_fields"].items()
}
FACT_FIELD_REQUIREMENTS = {kind: set(fields) for kind, fields in CONTRACT["fact_kinds"].items()}
FACT_KINDS = set(FACT_FIELD_REQUIREMENTS)
VALID_DISPOSITIONS = set(CONTRACT["dispositions"])
MATERIAL_SURFACES = set(CONTRACT["material_surfaces"])
REQUIRED = {tier: set(kinds) for tier, kinds in CONTRACT["tier_requirements"].items()}
REQUIRED_ATTACKS = set(CONTRACT["required_attacks"])
DOMAIN_ATTACKS = {domain: set(attacks) for domain, attacks in CONTRACT["domain_attacks"].items()}
OBLIGATIONS = {domain: tuple(obligations) for domain, obligations in CONTRACT["obligations"].items()}
OBLIGATION_ALIASES = {name: tuple(aliases) for name, aliases in CONTRACT["obligation_aliases"].items()}
BLUEPRINT_CONCEPTS = {
    domain: tuple(tuple(group) for group in groups) for domain, groups in CONTRACT["blueprint_concepts"].items()
}
BINDING_CATEGORIES = tuple(str(value) for value in CONTRACT["binding_categories"])
ARTIFACT_TYPES = set(CONTRACT["artifact_types"])
ID = re.compile(r"\b(?:SC|F|D|CH|P|B|O|C|R|T|X)-[1-9]\d*\b")
REC = re.compile(
    r"^\s*-\s+(?P<id>(?:SC|F|D|CH|P|B|O|C|R|T|X)-[1-9]\d*|A-(?:[1-9]\d*|[a-z][a-z-]*))\s*:\s*(?P<body>.+)$"
)
BP = re.compile(
    r"^### Execution Blueprint: (?P<changes>CH-[1-9]\d*(?:,\s*CH-[1-9]\d*)*) — (?P<purpose>.+) "
    r"\[type: (?P<type>[a-z-]+); domains: (?P<domains>none|[a-z-]+(?:,[a-z-]+)*)\]$"
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
    domains: tuple[str, ...]
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
            domains = () if m["domains"] == "none" else tuple(m["domains"].split(","))
            blueprints.append(
                Blueprint(
                    tuple(x.strip() for x in m["changes"].split(",")),
                    m["purpose"],
                    m["type"],
                    domains,
                    body,
                    n,
                    bp_section,
                )
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
    categorized: dict[str, set[str]] = {category: set() for category in BINDING_CATEGORIES}
    if plan:
        for record in plan.records.get("F", ()):
            raw = record.fields.get("path", "")
            category = (
                "config"
                if record.fields.get("kind") == "config-key"
                else "schemas"
                if record.fields.get("kind") == "schema-shape"
                else "evidence"
            )
            categorized[category].add(raw)
            if record.fields.get("kind") == "generated-from":
                categorized["generators"].add(record.fields.get("generator", ""))
        for record in plan.records.get("CH", ()):
            if record.fields.get("status") == "existing":
                categorized["targets"].add(record.fields.get("path", ""))
    bound: dict[str, list[dict[str, str]]] = {}
    for category, paths in categorized.items():
        bound[category] = []
        for raw in sorted(paths):
            resolved = _resolve(root, raw)
            if resolved and resolved.is_file():
                bound[category].append({"path": raw.replace("\\", "/"), "sha256": _hash(resolved.read_bytes())})
    return {
        "repository_id": (git("config", "--get", "remote.origin.url").stdout.strip() if is_git else "") or str(root.resolve()),
        "git": is_git,
        "git_head": git("rev-parse", "HEAD").stdout.strip() or None if is_git else None,
        "dirty": dirty,
        "tracked": tracked,
        "untracked": untracked,
        **bound,
    }


def binding_for(plan: Plan, root: Path) -> dict[str, Any]:
    value = snapshot(root, plan)
    # A finalized plan is intentionally insensitive to unrelated repository
    # activity.  The planning baseline remains exhaustive; this receipt binds
    # only evidence/targets/generator sources and dirty content on those paths.
    bound_paths = {
        item["path"] for category in BINDING_CATEGORIES for item in value.get(category, [])
    }
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


def _map_changes(expected: object, actual: object) -> list[str]:
    before = expected if isinstance(expected, dict) else {}
    after = actual if isinstance(actual, dict) else {}
    return sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )


def _snapshot_diagnostics(baseline: object, current: dict[str, Any]) -> list[Diagnostic]:
    if not isinstance(baseline, dict):
        return [Diagnostic("snapshot.malformed", "Planning baseline must be a snapshot object.")]
    diagnostics: list[Diagnostic] = []
    if baseline.get("repository_id") != current.get("repository_id") or baseline.get("git") != current.get("git"):
        diagnostics.append(Diagnostic("snapshot.repository_changed", "Repository identity or Git mode changed."))
    if baseline.get("git_head") != current.get("git_head"):
        diagnostics.append(
            Diagnostic(
                "snapshot.head_changed",
                f"Repository HEAD changed from {baseline.get('git_head')} to {current.get('git_head')}.",
            )
        )
    for category in ("dirty", "tracked", "untracked"):
        for path in _map_changes(baseline.get(category), current.get(category)):
            diagnostics.append(
                Diagnostic(f"snapshot.{category}_changed", f"{category} snapshot changed: {path}.")
            )
    return diagnostics


def _binding_diagnostics(expected: object, actual: dict[str, Any]) -> list[Diagnostic]:
    if not isinstance(expected, dict):
        return [Diagnostic("binding.malformed", "Repository binding must be an object.")]
    diagnostics: list[Diagnostic] = []
    for category in BINDING_CATEGORIES:
        before = {
            item.get("path"): item.get("sha256")
            for item in expected.get(category, [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        after = {
            item.get("path"): item.get("sha256")
            for item in actual.get(category, [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        for path in _map_changes(before, after):
            diagnostics.append(
                Diagnostic(f"binding.{category.rstrip('s')}_stale", f"Bound {category} item changed: {path}.")
            )
    for path in _map_changes(expected.get("dirty"), actual.get("dirty")):
        diagnostics.append(Diagnostic("binding.dirty_stale", f"Bound dirty path changed: {path}."))
    for field in ("repository_id", "git", "plan_body_sha256"):
        if expected.get(field) != actual.get(field):
            diagnostics.append(Diagnostic("binding.metadata_stale", f"Binding field changed: {field}."))
    return diagnostics


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


def _deferred(value: str) -> bool:
    """Reject placeholders that let a plan appear complete while deferring a decision."""
    return bool(re.search(r"\b(?:tbd|todo|later|as needed|if necessary|appropriate|determine|decide later|follow up)\b", value, re.I))


def _in_range(node: ast.AST, start: int, end: int) -> bool:
    lineno = getattr(node, "lineno", 0)
    end_lineno = getattr(node, "end_lineno", lineno)
    return start <= lineno <= end and end_lineno <= end


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _dotted_name(node.func)
    return ""


def _structured_error(ds: list[Diagnostic], fact: Record, detail: str) -> None:
    ds.append(Diagnostic("fact.structured", f"{fact.id}: {detail}", fact.line))


def _fact_fields(
    ds: list[Diagnostic],
    fact: Record,
    excerpt: str,
    source_text: str,
    source_path: Path,
    repo_root: Path,
) -> None:
    kind = fact.fields.get("kind", "")
    missing = FACT_FIELD_REQUIREMENTS.get(kind, set()) - set(fact.fields)
    for required in sorted(missing):
        ds.append(Diagnostic("fact.structured_required", f"{fact.id}: {kind} requires {required}.", fact.line))
    if missing:
        return
    start, end = map(int, fact.fields["lines"].split("-", 1))
    tree: ast.Module | None = None
    if source_path.suffix == ".py":
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            _structured_error(ds, fact, "Python structured evidence cannot be parsed.")
            return

    if kind == "function-signature":
        if tree is None:
            _structured_error(ds, fact, "function-signature requires Python source.")
            return
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == fact.fields.get("anchor")
            and start <= node.lineno <= end
        ]
        if not functions:
            ds.append(
                Diagnostic(
                    "fact.signature",
                    f"{fact.id}: cited anchor is not a Python function in the stated range.",
                    fact.line,
                )
            )
            return
        node = functions[0]
        async_claim = fact.fields.get("async")
        if async_claim not in {"true", "false"} or (async_claim == "true") != isinstance(node, ast.AsyncFunctionDef):
            _structured_error(ds, fact, "async must exactly match the cited function declaration.")
        try:
            claimed_tree = ast.parse(f"def _claimed({fact.fields['parameters']}) -> {fact.fields['returns']}:\n    pass\n")
            claimed = claimed_tree.body[0]
            assert isinstance(claimed, ast.FunctionDef)
            assert claimed.returns is not None
        except (SyntaxError, AssertionError):
            _structured_error(ds, fact, "claimed parameters or return annotation are not valid Python syntax.")
            return
        if ast.dump(claimed.args, include_attributes=False) != ast.dump(node.args, include_attributes=False):
            ds.append(
                Diagnostic(
                    "fact.signature_parameters",
                    f"{fact.id}: claimed parameters do not exactly match the Python signature.",
                    fact.line,
                )
            )
        claimed_return = ast.dump(claimed.returns, include_attributes=False)
        actual_return = ast.dump(node.returns, include_attributes=False) if node.returns is not None else ""
        if claimed_return != actual_return:
            ds.append(
                Diagnostic(
                    "fact.signature_returns",
                    f"{fact.id}: claimed return annotation does not exactly match the Python signature.",
                    fact.line,
                )
            )
        return

    if kind == "class-signature":
        if tree is None:
            _structured_error(ds, fact, "class-signature requires Python source.")
            return
        classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == fact.fields.get("anchor") and start <= node.lineno <= end
        ]
        if not classes:
            _structured_error(ds, fact, "cited anchor is not a Python class in the stated range.")
            return
        try:
            claimed_tree = ast.parse(f"class _Claimed({fact.fields['bases']}):\n    pass\n")
            claimed = claimed_tree.body[0]
            assert isinstance(claimed, ast.ClassDef)
        except (SyntaxError, AssertionError):
            _structured_error(ds, fact, "claimed bases are not valid Python syntax.")
            return
        actual = [ast.dump(base, include_attributes=False) for base in classes[0].bases]
        expected = [ast.dump(base, include_attributes=False) for base in claimed.bases]
        if actual != expected:
            _structured_error(ds, fact, "claimed bases do not match the cited class.")
        return

    if kind in {"call-edge", "external-call"}:
        if tree is None:
            _structured_error(ds, fact, f"{kind} requires Python source.")
            return
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _in_range(node, start, end)
            and _dotted_name(node.func) == fact.fields.get("callee")
        ]
        if kind == "call-edge":
            callers = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == fact.fields.get("caller")
                and start <= node.lineno <= end
            ]
            if not callers or not any(call in set(ast.walk(callers[0])) for call in calls):
                _structured_error(ds, fact, "qualified caller/callee edge is not contained in the cited range.")
        elif not calls:
            _structured_error(ds, fact, "qualified external call is not contained in the cited range.")
        return

    if kind in {"branch", "error", "side-effect"}:
        if tree is None:
            _structured_error(ds, fact, f"{kind} requires Python source.")
            return
        if kind == "branch":
            values = [
                ast.unparse(node.test)
                for node in ast.walk(tree)
                if isinstance(node, (ast.If, ast.While, ast.IfExp)) and _in_range(node.test, start, end)
            ]
            claim = fact.fields["condition"]
        elif kind == "error":
            values = [
                ast.unparse(node.exc)
                for node in ast.walk(tree)
                if isinstance(node, ast.Raise) and node.exc is not None and _in_range(node, start, end)
            ]
            claim = fact.fields["error"]
        else:
            values = [
                ast.unparse(node)
                for node in ast.walk(tree)
                if isinstance(node, (ast.Call, ast.Assign, ast.AugAssign, ast.Delete)) and _in_range(node, start, end)
            ]
            claim = fact.fields["effect"]
        if claim not in values and not any(claim in value for value in values):
            _structured_error(ds, fact, f"claimed {kind} is not structurally contained in the cited range.")
        return

    if kind == "schema-shape":
        claimed_fields = {value.strip() for value in fact.fields["fields"].split(",") if value.strip()}
        actual_fields: set[str] = set()
        if tree is not None:
            classes = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef) and node.name == fact.fields.get("anchor") and start <= node.lineno <= end
            ]
            if classes:
                actual_fields = {
                    node.target.id
                    for node in classes[0].body
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and _in_range(node, start, end)
                }
        elif source_path.suffix == ".json":
            try:
                schema_value = json.loads(source_text)
                schema = schema_value.get("properties", schema_value) if isinstance(schema_value, dict) else {}
                actual_fields = set(schema) if isinstance(schema, dict) else set()
            except json.JSONDecodeError:
                pass
        if claimed_fields != actual_fields:
            _structured_error(ds, fact, "claimed schema fields do not exactly match the cited schema.")
        return

    if kind == "config-key":
        key, config_expected = fact.fields["key"], fact.fields["value"]
        found = False
        if source_path.suffix == ".json":
            try:
                config_value: Any = json.loads(source_text)
                for part in key.split("."):
                    config_value = config_value[part] if isinstance(config_value, dict) else None
                found = json.dumps(config_value, sort_keys=True).strip('"') == config_expected
            except (json.JSONDecodeError, KeyError):
                pass
        elif source_path.suffix in {".toml", ".ini", ".cfg", ".yaml", ".yml"}:
            found = any(
                start <= number <= end and key in line and config_expected in line
                for number, line in enumerate(source_text.splitlines(), 1)
            )
        if not found or key.split(".")[-1] not in excerpt:
            _structured_error(ds, fact, "config key/value is not structurally contained in the cited range.")
        return

    if kind == "generated-from":
        generator = _resolve(repo_root, fact.fields["generator"])
        output = fact.fields["output"].replace("\\", "/")
        if (
            fact.fields["generator"].replace("\\", "/") != fact.fields.get("path", "").replace("\\", "/")
            or not output
            or not generator
            or not generator.is_file()
        ):
            _structured_error(ds, fact, "generated output and authoritative generator relationship is invalid.")
        elif output not in generator.read_text(encoding="utf-8", errors="replace") and Path(output).name not in generator.read_text(
            encoding="utf-8", errors="replace"
        ):
            _structured_error(ds, fact, "authoritative generator does not declare the cited output.")
        return

    if kind == "directory-ownership":
        directory = _resolve(repo_root, fact.fields["directory"])
        if not directory or not directory.is_dir() or source_path == directory or source_path.parent not in (directory, *directory.parents):
            _structured_error(ds, fact, "ownership manifest must be inside an ancestor of the declared directory.")


def _is_within_path(child: str, parent: str) -> bool:
    try:
        Path(child).relative_to(Path(parent))
        return True
    except ValueError:
        return False


def _valid_directory_owner(target: Record, owner: Record, repo_root: Path) -> bool:
    target_path = target.fields.get("path", "").replace("\\", "/")
    owner_path = owner.fields.get("path", "").replace("\\", "/")
    if not target_path or not owner_path or target_path == owner_path:
        return False
    if owner.id.startswith("F-") and owner.fields.get("kind") == "directory-ownership":
        directory = owner.fields.get("directory", "").replace("\\", "/").rstrip("/")
        return bool(directory) and _is_within_path(target_path, directory + "/")
    manifests = {"__init__.py", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"}
    return Path(owner_path).name in manifests and _is_within_path(target_path, Path(owner_path).parent.as_posix() + "/")


def _valid_generator_owner(target: Record, owner: Record, facts: dict[str, Record]) -> bool:
    target_path = target.fields.get("path", "").replace("\\", "/")
    owner_path = owner.fields.get("path", "").replace("\\", "/")
    if not target_path or target_path == owner_path:
        return False
    if owner.id.startswith("F-"):
        return (
            owner.fields.get("kind") == "generated-from"
            and owner.fields.get("output", "").replace("\\", "/") == target_path
            and owner.fields.get("generator", "").replace("\\", "/") != target_path
        )
    return any(
        fact.fields.get("kind") == "generated-from"
        and fact.fields.get("output", "").replace("\\", "/") == target_path
        and fact.fields.get("generator", "").replace("\\", "/") == owner_path
        for fact in facts.values()
    )


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
        if plan.tier == "high-risk" and not plan.domains:
            ds.append(Diagnostic("metadata.high_risk_domains", "High-risk plans require at least one final risk domain."))
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
            if kind in {"SC", "D", "CH", "T", "R"} and any(_deferred(value) for value in r.fields.values()):
                ds.append(Diagnostic("record.deferred", f"{r.id}: material planning records must not defer a decision or verification detail.", r.line))
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
        _fact_fields(ds, f, excerpt, "\n".join(source), path, repo_root)
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
        else:
            if not p or p.exists() or not p.parent.exists() or not (
                ch.fields.get("directory-owner") or ch.fields.get("generator-owner")
            ):
                ds.append(
                    Diagnostic(
                        "change.new_path", f"{ch.id}: new target must be absent, contained, and have a semantic owner.", ch.line
                    )
                )
            record_index = {record.id: record for record in plan.all_records()}
            directory_refs = _refs(ch.fields.get("directory-owner", ""))
            generator_refs = _refs(ch.fields.get("generator-owner", ""))
            if directory_refs and not any(
                ref in record_index and _valid_directory_owner(ch, record_index[ref], repo_root)
                for ref in directory_refs
            ):
                ds.append(
                    Diagnostic(
                        "change.directory_owner",
                        f"{ch.id}: directory-owner must prove ancestor package or manifest ownership.",
                        ch.line,
                    )
                )
            if generator_refs and not any(
                ref in record_index and _valid_generator_owner(ch, record_index[ref], facts)
                for ref in generator_refs
            ):
                ds.append(
                    Diagnostic(
                        "change.generator_owner",
                        f"{ch.id}: generator-owner must prove an authoritative generator declares this output.",
                        ch.line,
                    )
                )
        if any(
            fact.fields.get("kind") == "generated-from"
            and fact.fields.get("output", "").replace("\\", "/") == ch.fields.get("path", "").replace("\\", "/")
            for fact in facts.values()
        ) and not ch.fields.get("generator-owner"):
            ds.append(Diagnostic("change.generated_output", f"{ch.id}: generated output requires a generator owner; edit the authoritative source.", ch.line))
        change_words = re.findall(r"[A-Za-z0-9_/-]+", ch.fields.get("change", ""))
        if len(change_words) < 6 or len(set(change_words)) < 5:
            ds.append(Diagnostic("change.specificity", f"{ch.id}: change needs exact behavior, branches, errors, ordering, or side effects.", ch.line))
    for boundary in plan.records.get("B", ()):
        flow = boundary.fields.get("flow", "")
        if flow.count("->") < 2 or not _concrete(boundary.fields.get("class", "")):
            ds.append(Diagnostic("boundary.specificity", f"{boundary.id}: boundary traces need a concrete class and a three-stage flow.", boundary.line))
    expected_obligations = {d: set(OBLIGATIONS[d]) for d in plan.domains}
    seen_obligations: dict[str, set[str]] = defaultdict(set)
    obligation_ownership: dict[tuple[str, str, str, str], list[Record]] = defaultdict(list)
    record_index = {record.id: record for record in plan.all_records()}
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
        aliases = OBLIGATION_ALIASES.get(obligation, ())
        coverage = obligation_record.fields.get("coverage", "").casefold()
        change_text = " ".join(
            record_index[ref].fields.get("change", "")
            for ref in _refs(obligation_record.fields.get("changes", ""))
            if ref in record_index
        ).casefold()
        test_texts = [
            " ".join(record_index[ref].fields.get(field, "") for field in ("given", "when", "then")).casefold()
            for ref in _refs(obligation_record.fields.get("tests", ""))
            if ref in record_index
        ]
        if aliases and not any(alias in f"{coverage} {change_text}" for alias in aliases):
            ds.append(
                Diagnostic(
                    "obligation.coverage",
                    f"{obligation_record.id}: coverage and owning change must describe {obligation}.",
                    obligation_record.line,
                )
            )
        if aliases and not any(any(alias in test_text for alias in aliases) for test_text in test_texts):
            ds.append(
                Diagnostic(
                    "obligation.test_ownership",
                    f"{obligation_record.id}: a referenced T-n must verify {obligation} behavior.",
                    obligation_record.line,
                )
            )
        ownership_key = (
            obligation_record.fields.get("evidence", ""),
            obligation_record.fields.get("decision", ""),
            obligation_record.fields.get("changes", ""),
            obligation_record.fields.get("tests", ""),
        )
        obligation_ownership[ownership_key].append(obligation_record)
        seen_obligations[domain].add(obligation)
    for records in obligation_ownership.values():
        if len(records) > 1:
            for record in records:
                ds.append(
                    Diagnostic(
                        "obligation.generic_ownership",
                        f"{record.id}: obligations may not copy the same evidence, decision, change, and test ownership.",
                        record.line,
                    )
                )
    for d, needed in expected_obligations.items():
        for obligation_name in needed - seen_obligations[d]:
            ds.append(Diagnostic("obligation.required", f"{d}: missing obligation {obligation_name}."))
    attack_records = plan.records.get("A", ())
    attacks = {r.id[2:]: r for r in attack_records}
    needed_attacks = REQUIRED_ATTACKS | set().union(*(DOMAIN_ATTACKS.get(d, set()) for d in plan.domains))
    recognized_attacks = REQUIRED_ATTACKS | set().union(*DOMAIN_ATTACKS.values())
    for name, count in Counter(r.id[2:] for r in attack_records).items():
        if count > 1:
            ds.append(Diagnostic("attack.duplicate", f"A-{name}: attack names must be unique.", next(r.line for r in attack_records if r.id[2:] == name)))
    for r in attack_records:
        if r.id[2:] not in recognized_attacks:
            ds.append(Diagnostic("attack.unknown", f"{r.id}: attack is not recognized by plan-contract v5.", r.line))
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
    covered_domains: set[str] = set()
    for bp in plan.blueprints:
        if (
            bp.section != "Implementation Specification"
            or not bp.body
            or not bp.purpose
            or bp.artifact_type not in ARTIFACT_TYPES
            or not set(bp.changes) <= plan.ids("CH")
        ):
            ds.append(
                Diagnostic(
                    "blueprint.invalid",
                    "Blueprint must be non-empty, allowed, purposeful, and own existing changes.",
                    bp.line,
                )
            )
        if set(bp.domains) - plan.domains:
            ds.append(
                Diagnostic(
                    "blueprint.domain",
                    "Blueprint domains must be a subset of final risk domains.",
                    bp.line,
                )
            )
        if plan.tier == "standard" and bp.domains:
            ds.append(Diagnostic("blueprint.domain", "Standard blueprints must declare domains: none.", bp.line))
        covered_domains.update(bp.domains)
    if plan.tier == "high-risk" and covered_domains != plan.domains:
        missing = ", ".join(sorted(plan.domains - covered_domains)) or "none"
        extra = ", ".join(sorted(covered_domains - plan.domains)) or "none"
        ds.append(
            Diagnostic(
                "blueprint.domain_coverage",
                f"Blueprint domains must exactly cover final domains; missing={missing}; extra={extra}.",
            )
        )
    for domain in sorted(plan.domains):
        body = "\n".join(bp.body for bp in plan.blueprints if domain in bp.domains).casefold()
        for index, group in enumerate(BLUEPRINT_CONCEPTS[domain], 1):
            if not any(concept.casefold() in body for concept in group):
                ds.append(
                    Diagnostic(
                        "blueprint.domain_concept",
                        f"{domain}: blueprint coverage is missing concept group {index} ({', '.join(group)}).",
                    )
                )
    for test in plan.records.get("T", ()):
        command = test.fields.get("command", "").strip()
        if plan.tier != "tiny" and command in {"python -m pytest", "pytest", "npm test", "go test ./..."}:
            ds.append(Diagnostic("verification.generic_command", f"{test.id}: standard and high-risk plans need a targeted verification command.", test.line))
        if not all(_concrete(test.fields.get(field, "")) for field in ("given", "when", "then")):
            ds.append(Diagnostic("verification.specificity", f"{test.id}: given, when, and then must be exact observable behavior.", test.line))
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
    # Facts earn their place by grounding another record; self-references are not evidence use.
    used_facts = set().union(*(_refs(value) for record in plan.all_records() if record.id.split("-", 1)[0] != "F" for value in record.fields.values()))
    for fact_id in plan.ids("F") - used_facts:
        fact = facts[fact_id]
        ds.append(Diagnostic("fact.unused", f"{fact_id}: evidence must ground a decision, change, propagation, boundary, or attack.", fact.line))
    if baseline is not None:
        current = snapshot(repo_root)
        ds.extend(_snapshot_diagnostics(baseline, current))
    if require_finalized:
        if not plan.receipt or not plan.binding:
            ds.append(Diagnostic("receipt.missing", "Finalized v5 plan needs repository binding and receipt."))
        elif plan.receipt["body"] != plan_digest(text) or plan.receipt["binding"] != binding_digest(plan.binding):
            ds.append(Diagnostic("receipt.stale", "Plan receipt does not match plan body or binding."))
        else:
            ds.extend(_binding_diagnostics(plan.binding, binding_for(plan, repo_root)))
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
