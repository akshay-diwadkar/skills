"""Parse approved plans and scaffold the canonical implementation-run bundle."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "implementation-contract.json"
PLAN_MARKER_RE = re.compile(r"<!--\s*plan-contract:\s*(?P<version>\d+)\s*-->")
TIER_RE = re.compile(r"<!--\s*tier:\s*(?P<tier>tiny|standard|high-risk);\s*task-type:\s*(?P<task>[^;]+?)\s*-->")
ID_RE = re.compile(r"\b(?P<prefix>SC|CH|T|C|R)-(?P<number>\d+)\b")
SC_RE = re.compile(r"^- (?P<id>SC-\d+):\s*(?P<body>.+)$", re.MULTILINE)
CONSTRAINT_RE = re.compile(r"^- (?P<id>C-\d+):\s*(?P<body>.+)$", re.MULTILINE)
RISK_RE = re.compile(r"^- (?P<id>R-\d+)(?:\s+(?P<severity>P[0-3]))?:\s*(?P<body>.+)$", re.MULTILINE)
V2_CHANGE_RE = re.compile(
    r"^- (?P<id>CH-\d+): `(?P<path>[^`]+)` \| anchor: `(?P<anchor>[^`]+)` "
    r"\| status: (?P<status>existing|new) \| change: (?P<body>.+)$",
    re.MULTILINE,
)
LEGACY_CHANGE_RE = re.compile(
    r"^-?\s*(?P<id>CH-\d+):\s*(?:`(?P<path>[^`]+)`)?(?P<body>.+)$",
    re.MULTILINE,
)
V2_TEST_RE = re.compile(
    r"^- (?P<id>T-\d+): given: (?P<given>.+?) \| expect: (?P<expect>.+?) \| command: `(?P<command>[^`]+)`$",
    re.MULTILINE,
)
LEGACY_TEST_RE = re.compile(r"^-?\s*(?P<id>T-\d+):\s*(?P<body>.+)$", re.MULTILINE)
TRACE_RE = re.compile(
    r"^\|\s*(?P<criterion>(?:SC|C)-\d+)\s*\|\s*(?P<changes>CH-\d+(?:\s*,\s*CH-\d+)*)\s*"
    r"\|\s*(?P<tests>T-\d+(?:\s*,\s*T-\d+)*)\s*\|",
    re.MULTILINE,
)
PLACEHOLDER_RE = re.compile(r"\b(?:Replace(?: with)?|TBD|TODO)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f" line {self.line}:" if self.line is not None else ":"
        return f"{self.code}{location} {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "line": self.line}


@dataclass(frozen=True)
class NormalizedPlan:
    contract_version: int | str
    tier: str
    task_type: str
    success_criteria: list[dict[str, str]]
    changes: list[dict[str, str]]
    tests: list[dict[str, str]]
    constraints: list[dict[str, str]]
    risks: list[dict[str, str]]
    traceability: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "tier": self.tier,
            "task_type": self.task_type,
            "success_criteria": self.success_criteria,
            "changes": self.changes,
            "tests": self.tests,
            "constraints": self.constraints,
            "risks": self.risks,
            "traceability": self.traceability,
        }


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_version") != 1:
        raise ValueError("implementation contract must have contract_version 1")
    return contract


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes()) if path.is_file() else ""


def _line(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _traceability(text: str) -> list[dict[str, Any]]:
    return [
        {
            "criterion": match.group("criterion"),
            "changes": _split_ids(match.group("changes")),
            "tests": _split_ids(match.group("tests")),
        }
        for match in TRACE_RE.finditer(text)
    ]


def _validate_references(plan: NormalizedPlan) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    change_ids = {item["id"] for item in plan.changes}
    test_ids = {item["id"] for item in plan.tests}
    criterion_ids = {item["id"] for item in [*plan.success_criteria, *plan.constraints]}
    traced_changes: set[str] = set()
    traced_tests: set[str] = set()
    for row in plan.traceability:
        if row["criterion"] not in criterion_ids:
            diagnostics.append(Diagnostic("plan.trace.criterion", f"Unknown criterion {row['criterion']}."))
        for identifier in row["changes"]:
            traced_changes.add(identifier)
            if identifier not in change_ids:
                diagnostics.append(Diagnostic("plan.trace.change", f"Unknown change {identifier}."))
        for identifier in row["tests"]:
            traced_tests.add(identifier)
            if identifier not in test_ids:
                diagnostics.append(Diagnostic("plan.trace.test", f"Unknown test {identifier}."))
    for identifier in sorted(change_ids - traced_changes):
        diagnostics.append(Diagnostic("plan.change.untraced", f"Change {identifier} is not in traceability."))
    for identifier in sorted(test_ids - traced_tests):
        diagnostics.append(Diagnostic("plan.test.untraced", f"Test {identifier} is not in traceability."))
    return diagnostics


def _parse_v2(text: str, marker: re.Match[str], tier_match: re.Match[str]) -> tuple[NormalizedPlan, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    changes = [match.groupdict() for match in V2_CHANGE_RE.finditer(text)]
    tests = [match.groupdict() for match in V2_TEST_RE.finditer(text)]
    success = [{"id": match.group("id"), "body": match.group("body")} for match in SC_RE.finditer(text)]
    constraints = [{"id": match.group("id"), "body": match.group("body")} for match in CONSTRAINT_RE.finditer(text)]
    risks = [
        {"id": match.group("id"), "severity": match.group("severity") or "", "body": match.group("body")}
        for match in RISK_RE.finditer(text)
    ]
    if not success:
        diagnostics.append(Diagnostic("plan.v2.success.missing", "At least one SC-n record is required."))
    if not changes:
        diagnostics.append(Diagnostic("plan.v2.change.missing", "At least one canonical CH-n record is required."))
    if not tests:
        diagnostics.append(Diagnostic("plan.v2.test.missing", "At least one canonical T-n record is required."))
    for placeholder in PLACEHOLDER_RE.finditer(text):
        diagnostics.append(Diagnostic("plan.placeholder", f"Unresolved placeholder {placeholder.group(0)!r}.", _line(text, placeholder.start())))
    tier = tier_match.group("tier")
    if tier == "high-risk":
        for heading in ("## Compatibility and Rollout", "## Durable Rollback"):
            if heading not in text:
                diagnostics.append(Diagnostic("plan.high-risk.section", f"High-Risk plan requires {heading}."))
    plan = NormalizedPlan(
        contract_version=int(marker.group("version")),
        tier=tier,
        task_type=tier_match.group("task").strip(),
        success_criteria=success,
        changes=changes,
        tests=tests,
        constraints=constraints,
        risks=risks,
        traceability=_traceability(text),
    )
    if not plan.traceability:
        diagnostics.append(Diagnostic("plan.trace.missing", "Canonical traceability rows are required."))
    diagnostics.extend(_validate_references(plan))
    return plan, diagnostics


def _section_present(text: str, names: tuple[str, ...]) -> bool:
    return any(re.search(rf"^##?\s+.*{re.escape(name)}", text, re.IGNORECASE | re.MULTILINE) for name in names)


def _legacy_path(match: re.Match[str]) -> str:
    if match.group("path"):
        return match.group("path")
    inline = re.search(r"`(?P<path>[^`]+\.[A-Za-z0-9]+)`", match.group("body"))
    return inline.group("path") if inline else ""


def _parse_legacy(text: str) -> tuple[NormalizedPlan, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    id_types = {match.group("prefix") for match in ID_RE.finditer(text)}
    high_risk = all(_section_present(text, (name,)) for name in ("Compatibility", "Rollback"))
    if {"SC", "CH", "T"}.issubset(id_types):
        tier = "high-risk" if high_risk else "standard"
        changes = [
            {"id": match.group("id"), "path": _legacy_path(match), "anchor": "", "status": "existing", "body": match.group("body").strip()}
            for match in LEGACY_CHANGE_RE.finditer(text)
        ]
        tests = [
            {"id": match.group("id"), "given": "legacy", "expect": match.group("body").strip(), "command": command.group("command") if (command := re.search(r"`(?P<command>[^`]+)`", match.group("body"))) else ""}
            for match in LEGACY_TEST_RE.finditer(text)
        ]
        success = [{"id": match.group("id"), "body": match.group("body")} for match in SC_RE.finditer(text)]
        constraints = [{"id": match.group("id"), "body": match.group("body")} for match in CONSTRAINT_RE.finditer(text)]
        risks = [{"id": match.group("id"), "severity": match.group("severity") or "", "body": match.group("body")} for match in RISK_RE.finditer(text)]
        for change in changes:
            if not change["path"]:
                diagnostics.append(Diagnostic("plan.legacy.change.path", f"{change['id']} must name one target path in backticks."))
        for test in tests:
            if not test["command"]:
                diagnostics.append(Diagnostic("plan.legacy.test.command", f"{test['id']} must name one verification command in backticks."))
        plan = NormalizedPlan("legacy", tier, "external", success, changes, tests, constraints, risks, _traceability(text))
        if not plan.traceability:
            diagnostics.append(Diagnostic("plan.legacy.trace", "ID-based legacy plans require an unambiguous traceability table."))
        diagnostics.extend(_validate_references(plan))
        return plan, diagnostics

    required = {
        "outcome": _section_present(text, ("Outcome", "Goal")),
        "scope": _section_present(text, ("Scope",)),
        "change": _section_present(text, ("Change", "Implementation")),
        "verification": _section_present(text, ("Verification", "Test")),
    }
    for field, present in required.items():
        if not present:
            diagnostics.append(Diagnostic(f"plan.legacy.tiny.{field}", f"Legacy Tiny plan requires a concrete {field} section."))
    paths = re.findall(r"`([^`]+\.[A-Za-z0-9]+)`", text)
    commands = re.findall(r"`((?:python|pytest|npm|pnpm|yarn|cargo|go|dotnet|mvn|gradle)[^`]*)`", text)
    if not paths:
        diagnostics.append(Diagnostic("plan.legacy.tiny.path", "Legacy Tiny plan must name a target file in backticks."))
    if not commands:
        diagnostics.append(Diagnostic("plan.legacy.tiny.command", "Legacy Tiny plan must name a verification command in backticks."))
    plan = NormalizedPlan(
        "legacy",
        "tiny",
        "external",
        [{"id": "SC-1", "body": "Legacy Tiny observable outcome"}],
        [{"id": "CH-1", "path": paths[0] if paths else "", "anchor": "", "status": "existing", "body": "Legacy Tiny change"}],
        [{"id": "T-1", "given": "legacy", "expect": "Legacy Tiny verification", "command": commands[0] if commands else ""}],
        [],
        [],
        [{"criterion": "SC-1", "changes": ["CH-1"], "tests": ["T-1"]}],
    )
    return plan, diagnostics


def parse_plan(text: str) -> tuple[NormalizedPlan, list[Diagnostic]]:
    marker = PLAN_MARKER_RE.search(text)
    tier_match = TIER_RE.search(text)
    if marker:
        version = int(marker.group("version"))
        if version not in load_contract()["supported_plan_contract_versions"]:
            fallback = NormalizedPlan(version, "tiny", "unknown", [], [], [], [], [], [])
            return fallback, [Diagnostic("plan.version.unsupported", f"Unsupported plan contract version {version}.")]
        if tier_match is None:
            fallback = NormalizedPlan(version, "tiny", "unknown", [], [], [], [], [], [])
            return fallback, [Diagnostic("plan.tier.marker", "Versioned plan requires an explicit tier/task marker.")]
        return _parse_v2(text, marker, tier_match)
    if tier_match is not None:
        fallback = NormalizedPlan("legacy", tier_match.group("tier"), tier_match.group("task"), [], [], [], [], [], [])
        return fallback, [Diagnostic("plan.version.marker", "Tier marker requires a plan-contract marker.")]
    return _parse_legacy(text)


def git_status(repo_root: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    entries: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            path = line[3:].split(" -> ")[-1].strip('"').replace("\\", "/")
            entries[path] = line[:2]
    return entries


def git_value(repo_root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def output_is_ignored_or_external(repo_root: Path, output: Path) -> bool:
    root = repo_root.resolve()
    resolved = output.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return True
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative.as_posix()],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def scaffold_bundle(repo_root: Path, plan_path: Path, output_path: Path, run_id: str) -> dict[str, Any]:
    plan_text = plan_path.read_text(encoding="utf-8")
    plan, diagnostics = parse_plan(plan_text)
    if diagnostics:
        raise ValueError("invalid plan:\n  - " + "\n  - ".join(str(item) for item in diagnostics))
    if not output_is_ignored_or_external(repo_root, output_path):
        raise ValueError("output must be outside the repository or confirmed ignored by git check-ignore")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_path.parent / "plan.md"
    snapshot_path.write_text(plan_text, encoding="utf-8")
    dirty = git_status(repo_root)
    targets = sorted({item["path"] for item in plan.changes if item.get("path")})
    baseline_dir = output_path.parent / "baseline"
    target_records: list[dict[str, Any]] = []
    for relative in targets:
        source = repo_root / relative
        record = {
            "path": relative,
            "exists": source.is_file(),
            "sha256": sha256_file(source),
            "initial_status": dirty.get(relative, ""),
            "authorization": "",
        }
        target_records.append(record)
        if source.is_file():
            destination = baseline_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    initial_dirty = [
        {"path": path, "status": status, "sha256": sha256_file(repo_root / path)}
        for path, status in sorted(dirty.items())
    ]
    normalized = plan.to_dict()
    normalized.update({"source": str(plan_path), "sha256": sha256_bytes(plan_text.encode("utf-8"))})
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "in-progress",
        "plan": normalized,
        "workspace": {
            "repo_root": str(repo_root.resolve()),
            "commit": git_value(repo_root, "rev-parse", "HEAD"),
            "branch": git_value(repo_root, "branch", "--show-current"),
            "initial_dirty": initial_dirty,
            "targets": target_records,
            "baseline_dir": str(baseline_dir),
        },
        "baseline": [],
        "changes": [],
        "verification": [],
        "unresolved_changes": [item["id"] for item in plan.changes],
        "unresolved_tests": [item["id"] for item in plan.tests],
        "deviations": [],
        "final_workspace": {"changed_paths": [], "preserved_initial_dirty_paths": [], "concurrent_modifications": []},
        "residual_risks": [],
        "report": {"summary": "", "path": ""},
    }
