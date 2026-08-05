"""Plan-contract v7 parsing, targeted evidence verification, and sealing."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from _diagnostic_contract import normalize_diagnostic

CONTRACT_VERSION = 7
INTENTS = {"feature", "bug-fix", "refactor", "migration", "operational"}
TIERS = {"tiny", "standard", "high-risk"}
RISK_DOMAINS = {
    "security",
    "concurrency",
    "public-contract",
    "durable-state",
    "migration",
    "external-integration",
    "irreversible-external-effect",
}
HIGH_RISK_ONLY = {"security", "irreversible-external-effect"}
ROLLOUT_DOMAINS = {
    "public-contract",
    "durable-state",
    "migration",
    "external-integration",
    "irreversible-external-effect",
}
LOCALITIES = {"local", "shared", "test-only"}
REVERSIBILITIES = {"reversible", "conditional", "irreversible"}
RQ_SOURCES = {"request", "audit", "design", "optimization", "issue"}
RQ_CATEGORIES = {
    "decision",
    "constraint",
    "candidate",
    "workflow",
    "measure",
    "outcome",
    "protected-behavior",
    "obligation",
}
RQ_REQUIRED_CATEGORIES = {
    "design": frozenset({"decision", "constraint"}),
    "optimization": frozenset({"candidate", "workflow", "measure"}),
    "issue": frozenset({"outcome", "protected-behavior", "constraint"}),
}
PROPAGATION_SURFACES = {
    "caller",
    "consumer",
    "test",
    "fixture",
    "contract",
    "config",
    "schema",
    "generated",
    "deployment",
    "documentation",
}
HANDOFF_RECEIPT_RE = re.compile(
    r"^<!-- (?P<kind>audit|design|optimization|issue)-handoff: (?P<version>\d+); sha256: (?P<digest>[0-9a-f]{64}) -->$"
)
HANDOFF_LIKE_RE = re.compile(r"^<!-- [^>]*handoff[^>]*-->$", re.IGNORECASE)
REQUIRED_SECTIONS = ("Obligations", "Outcome", "Evidence", "Implementation", "Verification")
SECTION_ORDER = (
    "Obligations",
    "Outcome",
    "Evidence",
    "Decisions",
    "Implementation",
    "Propagation",
    "Boundaries and Risks",
    "Verification",
    "Rollout and Rollback",
)
RECORD_SECTIONS = {
    "RQ": "Obligations",
    "SC": "Outcome",
    "F": "Evidence",
    "D": "Decisions",
    "CH": "Implementation",
    "P": "Propagation",
    "B": "Boundaries and Risks",
    "R": "Boundaries and Risks",
    "T": "Verification",
}
FACT_FIELDS = {
    "source": set(),
    "function-signature": {"parameters", "returns", "async"},
    "class-signature": {"bases"},
    "call-edge": {"caller", "callee"},
    "external-call": {"callee"},
    "branch": {"condition"},
    "error": {"error"},
    "side-effect": {"effect"},
    "schema-shape": {"fields"},
    "config-key": {"key", "value"},
    "generated-from": {"generator", "output"},
    "directory-ownership": {"directory"},
}
REQUIRED_FIELDS = {
    "RQ": {"source", "anchor", "obligation", "covered_by"},
    "SC": {"given", "when", "then", "unchanged"},
    "F": {"kind", "path", "lines", "anchor", "claim"},
    "D": {"selected", "evidence", "rejected", "drawback"},
    "CH": {"path", "anchor", "status", "change", "depends_on", "locality", "reversibility"},
    "P": {"surface", "disposition", "path", "reason"},
    "B": {"class", "evidence", "flow"},
    "R": {"severity", "owner", "tests", "risk"},
    "T": {"covers", "given", "when", "then", "command"},
}
OPTIONAL_FIELDS = {
    "F": set().union(*FACT_FIELDS.values()),
    "RQ": {"category"},
    "CH": {"evidence", "owner"},
    "P": {"owner"},
}
OPTIONAL_SECTIONS = set(SECTION_ORDER) - set(REQUIRED_SECTIONS)
REFERENCE_FIELDS = {
    "RQ": {"covered_by": {"SC", "CH", "T"}},
    "D": {"evidence": {"F"}},
    "CH": {"evidence": {"F"}, "owner": {"F", "CH"}, "depends_on": {"CH"}},
    "P": {"owner": {"CH"}},
    "B": {"evidence": {"F"}},
    "R": {"owner": {"CH"}, "tests": {"T"}},
    "T": {"covers": {"SC", "CH"}},
}
RECORD_RE = re.compile(r"^\s*(?:-\s+)?(?P<id>(?:RQ|SC|F|D|CH|P|B|R|T)-[1-9]\d*): (?P<body>\S.*?)\s*$")
RECORD_LIKE_RE = re.compile(r"^\s*(?:-\s*)?(?P<prefix>RQ|SC|F|D|CH|P|B|R|T)-")
RECORD_TARGET_RE = re.compile(r"^\s*(?:-\s*)?(?P<record>(?:RQ|SC|F|D|CH|P|B|R|T)-[^\s:|]*)")
ID_RE = re.compile(r"\b(?:RQ|SC|F|D|CH|P|B|R|T)-[1-9]\d*\b")
DEPENDS_NONE_RE = re.compile(r"^none$")
PROOF_RE = re.compile(r"^<!-- plan-proof: (?P<json>.+) -->$", re.MULTILINE)
VALIDATION_RE = re.compile(
    r"^<!-- plan-validation: 7; body-sha256: (?P<body>[0-9a-f]{64}); proof-sha256: (?P<proof>[0-9a-f]{64}) -->$",
    re.MULTILINE,
)
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?!\[[\sxX ]?\])(.+?)\s*$")
CHECKLIST_ITEM_RE = re.compile(r"^\s*[-*+]\s+\[\s*[xX ]?\s*\]\s+(.+?)\s*$")
AC_HEADER_RE = re.compile(r"^(?:#{1,6}\s*)?acceptance criteria\b\s*:?\s*$", re.I)
NORMATIVE_HEADER_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:requirements|acceptance criteria|constraints)\b\s*:?\s*$",
    re.I,
)
SKIP_SECTION_HEADER_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:examples?|alternatives|notes|background)\b\s*:?\s*$",
    re.I,
)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
CONSTRAINT_CLAUSE_RE = re.compile(
    r"(?is)(?P<clause>(?:^|(?<=[\n.!?]))[^.!?\n]*\b(?:must|do not|don't|preserve|without)\b[^.!?\n]*)"
)
TRIVIAL_ANCHOR_WORDS = frozenset(
    {"fix", "and", "the", "a", "an", "or", "to", "of", "in", "on", "for", "is", "be", "as", "at", "by", "with"}
)
IDENTIFIER_LIKE_RE = re.compile(
    r"^(?:"
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+"
    r"|--?[A-Za-z][A-Za-z0-9_-]*"
    r"|[A-Z][A-Z0-9_]*"
    r"|[a-z]+(?:_[a-z0-9]+)+"
    r"|[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+"
    r"|[A-Za-z0-9_]+\.[A-Za-z0-9_.-]+"
    r")$"
)
TREE_SITTER_GRAMMARS = {
    ".js": ("tree_sitter_javascript", "language"),
    ".jsx": ("tree_sitter_javascript", "language"),
    ".ts": ("tree_sitter_typescript", "language_typescript"),
    ".tsx": ("tree_sitter_typescript", "language_tsx"),
    ".kt": ("tree_sitter_kotlin", "language"),
    ".kts": ("tree_sitter_kotlin", "language"),
    ".go": ("tree_sitter_go", "language"),
    ".java": ("tree_sitter_java", "language"),
    ".rs": ("tree_sitter_rust", "language"),
    ".rb": ("tree_sitter_ruby", "language"),
}
ROLLOUT_REQUIREMENTS = {
    "deployment/ordering": re.compile(
        r"\b(?:deploy|release|rollout|phase|batch|canary|traffic|order|sequence|compatibility window)\w*\b",
        re.I,
    ),
    "rollback/roll-forward action": re.compile(
        r"\b(?:roll\s*back|rollback|roll\s*forward|restore|revert|disable|compensat\w*|resume|retry)\b",
        re.I,
    ),
    "trigger/condition": re.compile(
        r"\b(?:if|when|upon|trigger\w*|threshold|divergen\w*|mismatch\w*|abort\w*|stop\s+on|on\s+(?:error|failure))\b",
        re.I,
    ),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _refs(value: str) -> set[str]:
    return set(ID_RE.findall(value))


def _substantive(value: str, minimum_words: int = 2) -> bool:
    if re.search(r"\b(?:TBD|TODO|FIXME|later|as needed|if necessary|decide later)\b", value, re.I):
        return False
    return len(re.findall(r"[A-Za-z0-9_./-]+", value)) >= minimum_words


def _is_trivial_anchor(anchor: str) -> bool:
    tokens = re.findall(r"[A-Za-z0-9_./-]+", anchor.lower())
    if not tokens:
        return True
    return all(token in TRIVIAL_ANCHOR_WORDS for token in tokens)


def _is_identifier_like(token: str) -> bool:
    return bool(IDENTIFIER_LIKE_RE.fullmatch(token))


def _is_weak_anchor(anchor: str) -> bool:
    if _is_trivial_anchor(anchor):
        return True
    tokens = re.findall(r"[A-Za-z0-9_./-]+", anchor)
    if len(tokens) == 1 and not _is_identifier_like(tokens[0]):
        return True
    return False


def _request_text_without_fences(request_text: str) -> str:
    return FENCE_RE.sub("\n", request_text)


def _blank_skip_sections(request_text: str) -> str:
    lines: list[str] = []
    in_skip = False
    for raw_line in request_text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = raw_line.strip()
        if SKIP_SECTION_HEADER_RE.match(stripped):
            in_skip = True
            lines.append("")
            continue
        if stripped.startswith("#"):
            in_skip = False
        lines.append("" if in_skip else raw_line)
    return "\n".join(lines)


def extract_structured_request_items(request_text: str) -> list[str]:
    """Extract blocking normative items only (not examples, fences, or unlabeled prose lists)."""
    items: list[str] = []
    seen: set[str] = set()

    def _add(item: str) -> None:
        cleaned = " ".join(item.split()).strip(" :-")
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        items.append(cleaned)

    scannable = _blank_skip_sections(_request_text_without_fences(request_text))
    in_normative = False
    for raw_line in scannable.splitlines():
        stripped = raw_line.strip()
        if NORMATIVE_HEADER_RE.match(stripped) or AC_HEADER_RE.match(stripped):
            in_normative = True
            continue
        if stripped.startswith("#"):
            in_normative = False
            continue
        checklist = CHECKLIST_ITEM_RE.match(raw_line)
        if checklist:
            _add(checklist.group(1))
            continue
        if in_normative:
            list_match = LIST_ITEM_RE.match(raw_line)
            if list_match:
                _add(list_match.group(1))
                continue
            if stripped and _substantive(stripped, 2):
                _add(stripped)

    for match in CONSTRAINT_CLAUSE_RE.finditer(scannable):
        clause = " ".join(match.group("clause").split()).strip(" :-")
        if not clause:
            continue
        if any(clause in item for item in items):
            continue
        if _substantive(clause, 2):
            _add(clause)
    return items


@dataclasses.dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    required_action: str
    record: str | None = None
    path: str | None = None
    line: int | None = None
    category: str = "contract_contradiction"

    def __str__(self) -> str:
        location = f"{self.record}: " if self.record else ""
        return f"{self.code}: {location}{self.message}"

    def to_dict(self, *, artifact: str = "draft.md") -> dict[str, Any]:
        supporting = [self.message]
        if self.line:
            supporting.append(f"draft line {self.line}")
        return normalize_diagnostic(
            {
                "code": self.code,
                "category": self.category,
                "message": self.message,
                "record": self.record,
                "path": self.path or artifact,
                "required_action": self.required_action,
                "valid_repairs": [self.required_action],
                "supporting_evidence": supporting,
                "why_it_matters": "The plan cannot be sealed until this exact contract or evidence defect is repaired.",
                "hint": self.required_action,
                "details": {"line": self.line} if self.line else {},
            },
            skill="plan-change",
            phase="run",
            artifact=artifact,
            path=self.path or artifact,
        )


@dataclasses.dataclass(frozen=True)
class Record:
    id: str
    fields: dict[str, str]
    line: int
    section: str


@dataclasses.dataclass(frozen=True)
class Plan:
    title: str
    metadata: dict[str, Any]
    sections: tuple[str, ...]
    records: dict[str, tuple[Record, ...]]
    text: str
    binding: dict[str, Any] | None = None
    receipt: dict[str, str] | None = None

    @property
    def tier(self) -> str:
        return str(self.metadata.get("tier", ""))

    @property
    def risk_domains(self) -> set[str]:
        value = self.metadata.get("risk_domains", [])
        return set(value) if isinstance(value, list) else set()

    def all_records(self) -> Iterable[Record]:
        return (record for records in self.records.values() for record in records)

    def ids(self, kind: str | None = None) -> set[str]:
        records = self.records.get(kind, ()) if kind else self.all_records()
        return {record.id for record in records}

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "title": self.title,
            "metadata": self.metadata,
            "records": {
                kind: [dataclasses.asdict(record) for record in records]
                for kind, records in self.records.items()
            },
        }


@dataclasses.dataclass
class RepositoryFile:
    path: Path
    relative: str
    data: bytes
    text: str
    lines: list[str]
    sha256: str | None = None
    python_ast: ast.AST | None = None
    python_parsed: bool = False
    tree: Any | None = None
    tree_parsed: bool = False
    tree_available: bool = False


class RepositoryView:
    """Read and parse only explicitly requested repository files, once per run."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        if not self.repo_root.is_dir():
            raise ValueError(f"repository root is not a directory: {self.repo_root}")
        self._files: dict[str, RepositoryFile] = {}
        self.opened_paths: list[str] = []
        self.bytes_read = 0
        self.hash_count = 0
        self.python_parse_count = 0
        self.tree_parse_count = 0
        self.git_command_count = 0
        self._identity: tuple[str, str | None] | None = None

    def resolve(self, raw: str) -> Path:
        normalized = raw.replace("\\", "/")
        candidate = (self.repo_root / normalized).resolve()
        if not raw or Path(normalized).is_absolute() or ".." in Path(normalized).parts:
            raise ValueError("path is empty, absolute, or traverses a parent")
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("path escapes repository root") from exc
        return candidate

    def get(self, raw: str) -> RepositoryFile:
        path = self.resolve(raw)
        relative = path.relative_to(self.repo_root).as_posix()
        if relative not in self._files:
            if not path.is_file():
                raise FileNotFoundError(relative)
            data = path.read_bytes()
            text = data.decode("utf-8", errors="replace")
            self._files[relative] = RepositoryFile(path, relative, data, text, text.splitlines())
            self.opened_paths.append(relative)
            self.bytes_read += len(data)
        return self._files[relative]

    def digest(self, raw: str) -> str:
        entry = self.get(raw)
        if entry.sha256 is None:
            entry.sha256 = _sha256(entry.data)
            self.hash_count += 1
        return entry.sha256

    def parse_python(self, raw: str) -> ast.AST:
        entry = self.get(raw)
        if not entry.python_parsed:
            entry.python_ast = ast.parse(entry.text)
            entry.python_parsed = True
            self.python_parse_count += 1
        assert entry.python_ast is not None
        return entry.python_ast

    def parse_tree(self, raw: str) -> tuple[Any | None, bool]:
        entry = self.get(raw)
        if entry.tree_parsed:
            return entry.tree, entry.tree_available
        entry.tree_parsed = True
        self.tree_parse_count += 1
        language: Any | None = None
        suffix = entry.path.suffix.lower()
        try:
            from tree_sitter import Language, Parser

            module_name, attribute = TREE_SITTER_GRAMMARS.get(suffix, ("", ""))
            if module_name:
                module = __import__(module_name)
                language = Language(getattr(module, attribute)())
                parser = Parser(language)
                entry.tree = parser.parse(entry.data)
                entry.tree_available = True
        except (ImportError, AttributeError, TypeError, ValueError):
            entry.tree = None
            entry.tree_available = False
        return entry.tree, entry.tree_available

    def repository_identity(self) -> tuple[str, str | None]:
        if self._identity is not None:
            return self._identity
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree", "HEAD"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.git_command_count += 1
        lines = probe.stdout.splitlines()
        if probe.returncode == 0 and len(lines) >= 2 and lines[0].strip() == "true":
            head = lines[-1].strip()
            remote = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.git_command_count += 1
            identity = remote.stdout.strip() or str(self.repo_root)
            self._identity = identity, head or None
        else:
            self._identity = str(self.repo_root), None
        return self._identity

    def counters(self) -> dict[str, Any]:
        return {
            "opened_paths": sorted(self.opened_paths),
            "bytes_read": self.bytes_read,
            "hash_count": self.hash_count,
            "python_parse_count": self.python_parse_count,
            "tree_parse_count": self.tree_parse_count,
            "git_command_count": self.git_command_count,
        }


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    plan: Plan | None
    diagnostics: tuple[Diagnostic, ...]
    fact_proofs: tuple[dict[str, str], ...]
    view: RepositoryView

    @property
    def valid(self) -> bool:
        return self.plan is not None and not self.diagnostics


@dataclasses.dataclass(frozen=True)
class SealResult:
    text: str
    proof: dict[str, Any]
    counters: dict[str, Any]


def _fields(raw: str, record: str, line: int, diagnostics: list[Diagnostic]) -> dict[str, str]:
    fields: dict[str, str] = {}
    parts = raw.split(" | ")
    invalid = any("|" in part for part in parts)
    for part in parts:
        key, separator, value = part.partition(": ")
        normalized_value = value.strip("`")
        if (
            not separator
            or re.fullmatch(r"[a-z][a-z0-9_-]*", key) is None
            or not normalized_value
            or value != value.strip()
            or key in fields
        ):
            invalid = True
            continue
        fields[key] = normalized_value
    if invalid:
        diagnostics.append(
            Diagnostic(
                "record.invalid",
                "Fields must be unique non-empty 'key: value' pairs separated by exact ' | ' delimiters.",
                f"Correct the field syntax for {record}.",
                record,
                line=line,
            )
        )
    return fields


def _section_has_substance(lines: Iterable[str]) -> bool:
    text = "\n".join(lines)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>\n]+>", " ", text)
    text = re.sub(r"\b(?:TBD|TODO|FIXME|later|as needed|if necessary|decide later)\b", " ", text, flags=re.I)
    text = ID_RE.sub(" ", text)
    text = re.sub(r"\b[a-z][a-z0-9_-]*:\s*", " ", text)
    text = re.sub(r"[#*`|:\-]+", " ", text)
    return len(re.findall(r"[A-Za-z0-9_./]+", text)) >= 2


def _section_diagnostics(
    sections: dict[str, list[str]], heading_lines: dict[str, int], _risk_domains: set[str]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    empty_sections: set[str] = set()
    for section in SECTION_ORDER:
        if section not in OPTIONAL_SECTIONS or section not in sections:
            continue
        if not _section_has_substance(sections[section]):
            empty_sections.add(section)
            diagnostics.append(
                Diagnostic(
                    "section.empty",
                    f"{section} is empty or placeholder-only.",
                    f"Remove {section} or add substantive content.",
                    line=heading_lines[section],
                )
            )
    if "Rollout and Rollback" in sections and "Rollout and Rollback" not in empty_sections:
        rollout = "\n".join(sections["Rollout and Rollback"])
        missing = [name for name, pattern in ROLLOUT_REQUIREMENTS.items() if pattern.search(rollout) is None]
        if missing:
            diagnostics.append(
                Diagnostic(
                    "rollout.invalid",
                    f"Rollout and Rollback is missing: {', '.join(missing)}.",
                    "Add concrete deployment order, recovery action, and its trigger condition.",
                    line=heading_lines["Rollout and Rollback"],
                )
            )
    return diagnostics


def parse_plan(text: str) -> tuple[Plan | None, list[Diagnostic]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    diagnostics: list[Diagnostic] = []
    contract_matches = re.findall(r"<!--\s*plan-contract:\s*(\d+)\s*-->", normalized)
    if contract_matches != ["7"]:
        return None, [
            Diagnostic(
                "contract.unsupported",
                "Exactly one plan-contract version 7 marker is required.",
                "Replace the contract marker with '<!-- plan-contract: 7 -->'.",
            )
        ]
    if PROOF_RE.search(normalized) or VALIDATION_RE.search(normalized):
        diagnostics.append(
            Diagnostic(
                "record.invalid",
                "Drafts must not contain plan-proof or plan-validation markers.",
                "Remove machine-generated proof and validation markers from the draft.",
            )
        )
    title_matches = re.findall(r"^# (.+)$", normalized, re.MULTILINE)
    if len(title_matches) != 1 or not _substantive(title_matches[0] if title_matches else ""):
        diagnostics.append(
            Diagnostic("record.invalid", "One substantive level-one title is required.", "Add one action-oriented '# Title'.")
        )
    metadata_matches = re.findall(r"^<!-- plan-metadata: (.+) -->$", normalized, re.MULTILINE)
    metadata: dict[str, Any] = {}
    if len(metadata_matches) != 1:
        diagnostics.append(
            Diagnostic("metadata.invalid", "Exactly one plan-metadata marker is required.", "Add one valid v7 metadata marker.")
        )
    else:
        try:
            value = json.loads(metadata_matches[0])
            if not isinstance(value, dict) or set(value) != {"intent", "tier", "risk_domains"}:
                raise ValueError
            metadata = value
        except (json.JSONDecodeError, ValueError):
            diagnostics.append(
                Diagnostic(
                    "metadata.invalid",
                    "Metadata must contain only intent, tier, and risk_domains.",
                    "Correct the plan-metadata JSON object.",
                )
            )
    heading_matches = list(re.finditer(r"^## (.+)$", normalized, re.MULTILINE))
    headings = tuple(match.group(1).strip() for match in heading_matches)
    heading_lines = {
        match.group(1).strip(): normalized.count("\n", 0, match.start()) + 1 for match in heading_matches
    }
    expected = tuple(section for section in SECTION_ORDER if section in headings)
    if any(section not in headings for section in REQUIRED_SECTIONS) or headings != expected or len(set(headings)) != len(headings):
        diagnostics.append(
            Diagnostic(
                "section.order",
                "Required and conditional sections must occur once in canonical v7 order.",
                "Reorder sections to the canonical v7 sequence and add missing required sections.",
            )
        )
    records: dict[str, list[Record]] = defaultdict(list)
    section_lines: dict[str, list[str]] = defaultdict(list)
    current_section = ""
    for number, line_text in enumerate(normalized.splitlines(), 1):
        if line_text.startswith("## "):
            current_section = line_text[3:].strip()
            continue
        if current_section in SECTION_ORDER:
            section_lines[current_section].append(line_text)
        match = RECORD_RE.match(line_text)
        record_like = RECORD_LIKE_RE.match(line_text)
        if record_like and not match:
            target_match = RECORD_TARGET_RE.match(line_text)
            target = target_match.group("record") if target_match else f"{record_like.group('prefix')}-"
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    "Record-like lines must use a positive integer ID, ': ', and a non-empty field body.",
                    f"Correct the record syntax for {target} on this line.",
                    target,
                    line=number,
                )
            )
            continue
        if not match:
            continue
        identifier = match.group("id")
        kind = identifier.split("-", 1)[0]
        records[kind].append(Record(identifier, _fields(match.group("body"), identifier, number, diagnostics), number, current_section))
    all_ids = [record.id for group in records.values() for record in group]
    for duplicate in sorted({identifier for identifier in all_ids if all_ids.count(identifier) > 1}):
        diagnostics.append(
            Diagnostic("record.invalid", "Record ID is duplicated.", f"Rename or remove duplicate {duplicate}.", duplicate)
        )
    domains = metadata.get("risk_domains", [])
    risk_domains = set(domains) if isinstance(domains, list) and all(isinstance(item, str) for item in domains) else set()
    diagnostics.extend(_section_diagnostics(section_lines, heading_lines, risk_domains))
    return (
        Plan(
            title_matches[0] if len(title_matches) == 1 else "",
            metadata,
            headings,
            {kind: tuple(group) for kind, group in records.items()},
            normalized.rstrip() + "\n",
        ),
        diagnostics,
    )


def _metadata_diagnostics(plan: Plan) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    intent, tier, domains = plan.metadata.get("intent"), plan.metadata.get("tier"), plan.metadata.get("risk_domains")
    if intent not in INTENTS or tier not in TIERS or not isinstance(domains, list) or not all(isinstance(item, str) for item in domains):
        return [Diagnostic("metadata.invalid", "Metadata contains unsupported values.", "Use a supported intent, tier, and string risk-domain list.")]
    if len(domains) != len(set(domains)) or set(domains) - RISK_DOMAINS:
        diagnostics.append(Diagnostic("metadata.invalid", "Risk domains must be unique supported values.", "Correct metadata.risk_domains."))
    if tier == "tiny" and domains:
        diagnostics.append(Diagnostic("metadata.invalid", "Tiny plans cannot declare risk domains.", "Raise the tier or remove risk domains."))
    if tier == "high-risk" and not domains:
        diagnostics.append(Diagnostic("metadata.invalid", "High-risk plans require at least one risk domain.", "Declare the applicable risk domain."))
    if tier != "high-risk" and HIGH_RISK_ONLY & set(domains):
        diagnostics.append(Diagnostic("metadata.invalid", "Security and irreversible effects require high-risk tier.", "Set tier to high-risk."))
    return diagnostics


def _change_id_sort_key(identifier: str) -> tuple[int, str]:
    try:
        return int(identifier.split("-", 1)[1]), identifier
    except (IndexError, ValueError):
        return 10**9, identifier


def _depends_on_ids(raw: str) -> tuple[set[str], bool]:
    value = raw.strip()
    if DEPENDS_NONE_RE.fullmatch(value):
        return set(), False
    refs = _refs(value)
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    invalid = bool(tokens) and (
        any(DEPENDS_NONE_RE.fullmatch(token) for token in tokens)
        or any(re.fullmatch(r"CH-[1-9]\d*", token) is None for token in tokens)
        or len(tokens) != len(refs)
    )
    return refs, invalid


def topological_change_order(plan: Plan) -> tuple[list[str], list[Diagnostic]]:
    """Return deterministic CH order from depends_on, or diagnostics on cycles/missing deps."""
    diagnostics: list[Diagnostic] = []
    changes = {record.id: record for record in plan.records.get("CH", ())}
    if not changes:
        return [], diagnostics
    edges: dict[str, set[str]] = {identifier: set() for identifier in changes}
    indegree = {identifier: 0 for identifier in changes}
    for change in changes.values():
        deps, invalid = _depends_on_ids(change.fields.get("depends_on", ""))
        if invalid:
            diagnostics.append(
                Diagnostic(
                    "dependency.invalid",
                    "depends_on must be 'none' or a unique comma-separated CH list.",
                    f"Correct {change.id}.depends_on.",
                    change.id,
                    line=change.line,
                )
            )
            continue
        for dep in sorted(deps, key=_change_id_sort_key):
            if dep == change.id:
                diagnostics.append(
                    Diagnostic(
                        "dependency.cycle",
                        "Change depends on itself.",
                        f"Remove the self-dependency from {change.id}.depends_on.",
                        change.id,
                        line=change.line,
                    )
                )
                continue
            if dep not in changes:
                diagnostics.append(
                    Diagnostic(
                        "dependency.missing",
                        f"Unknown dependency {dep}.",
                        f"Correct {change.id}.depends_on.",
                        change.id,
                        line=change.line,
                    )
                )
                continue
            if change.id not in edges[dep]:
                edges[dep].add(change.id)
                indegree[change.id] += 1
    if diagnostics:
        return [], diagnostics
    ready = sorted((identifier for identifier, count in indegree.items() if count == 0), key=_change_id_sort_key)
    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for child in sorted(edges[current], key=_change_id_sort_key):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort(key=_change_id_sort_key)
    if len(ordered) != len(changes):
        remaining = sorted(set(changes) - set(ordered), key=_change_id_sort_key)
        for identifier in remaining:
            diagnostics.append(
                Diagnostic(
                    "dependency.cycle",
                    "Change dependency graph contains a cycle.",
                    f"Break the cycle involving {identifier}.",
                    identifier,
                    line=changes[identifier].line,
                )
            )
        return [], diagnostics
    return ordered, diagnostics


def _audit_finding_section(request_text: str, finding_id: str) -> str:
    heading = re.compile(rf"^## Issue {re.escape(finding_id)}\s*$", re.MULTILINE)
    match = heading.search(request_text)
    if match is None:
        return ""
    next_heading = re.search(r"^## Issue \S+\s*$", request_text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(request_text)
    return request_text[match.start() : end]


def _markdown_section(request_text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", request_text, re.MULTILINE)
    if match is None:
        return ""
    next_heading = re.search(r"^## .+$", request_text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(request_text)
    return request_text[match.start() : end]


def _selected_handoff_material(kind: str, request_text: str, request_source: dict[str, Any] | None) -> str:
    if kind == "audit":
        selected = request_source.get("item") if isinstance(request_source, dict) else None
        if isinstance(selected, str) and selected:
            return _audit_finding_section(request_text, selected)
        return ""
    if kind == "design":
        return _markdown_section(request_text, "Chosen Design & Depth Rationale")
    if kind == "optimization":
        handoff_match = re.search(
            r"^- H-\d+:[^\n]*\bnext:\s*plan-ready\b[^\n]*$",
            request_text,
            re.MULTILINE | re.IGNORECASE,
        )
        if handoff_match is None:
            return ""
        line = handoff_match.group(0)
        candidate_match = re.search(r"\bcandidate:\s*([A-Za-z0-9_-]+)", line, re.IGNORECASE)
        chunks = [line]
        selected_line = re.search(r"^- Selected candidate:\s*.+$", request_text, re.MULTILINE | re.IGNORECASE)
        if selected_line is not None:
            chunks.append(selected_line.group(0))
        if candidate_match is not None:
            candidate_id = candidate_match.group(1)
            candidate_heading = re.search(
                rf"^##+\s+.*\b{re.escape(candidate_id)}\b.*$",
                request_text,
                re.MULTILINE | re.IGNORECASE,
            )
            if candidate_heading is not None:
                next_heading = re.search(r"^##+.+$", request_text[candidate_heading.end() :], re.MULTILINE)
                end = (
                    candidate_heading.end() + next_heading.start()
                    if next_heading
                    else len(request_text)
                )
                chunks.append(request_text[candidate_heading.start() : end])
            else:
                candidate_line = re.search(
                    rf"^- {re.escape(candidate_id)}:[^\n]*$",
                    request_text,
                    re.MULTILINE,
                )
                if candidate_line is not None:
                    chunks.append(candidate_line.group(0))
        return "\n".join(chunks)
    if kind == "issue":
        return "\n".join(
            section
            for heading in ("Outcome and Scope", "Constraints and Protected Behavior")
            if (section := _markdown_section(request_text, heading))
        )
    return ""


def _obligation_diagnostics(
    plan: Plan,
    request_bytes: bytes | None,
    request_source: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    obligations = plan.records.get("RQ", ())
    if not obligations:
        diagnostics.append(Diagnostic("record.invalid", "At least one RQ record is required.", "Add a concrete RQ-1 record."))
        return diagnostics
    request_text = ""
    if request_bytes is not None:
        try:
            request_text = request_bytes.decode("utf-8")
        except UnicodeDecodeError:
            diagnostics.append(
                Diagnostic(
                    "request.encoding",
                    "Request files must be valid UTF-8 for obligation anchors.",
                    "Provide a UTF-8 request or handoff file.",
                )
            )
            return diagnostics
    for record in obligations:
        source = record.fields.get("source", "")
        if source not in RQ_SOURCES:
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    "Obligation source must be request, audit, design, optimization, or issue.",
                    f"Correct {record.id}.source.",
                    record.id,
                    line=record.line,
                )
            )
        if not _substantive(record.fields.get("obligation", ""), 3):
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    "Obligation text must be concrete.",
                    f"Make {record.id}.obligation material and specific.",
                    record.id,
                    line=record.line,
                )
            )
        anchor = record.fields.get("anchor", "")
        if not anchor.strip():
            diagnostics.append(
                Diagnostic(
                    "obligation.anchor",
                    "Obligation anchor is empty.",
                    f"Set {record.id}.anchor to exact request or handoff text.",
                    record.id,
                    line=record.line,
                )
            )
        elif request_bytes is not None and anchor not in request_text:
            diagnostics.append(
                Diagnostic(
                    "obligation.anchor",
                    "Obligation anchor is absent from the request or handoff.",
                    f"Copy exact text into {record.id}.anchor from the sealed request.",
                    record.id,
                    line=record.line,
                )
            )
        refs = _refs(record.fields.get("covered_by", ""))
        kinds = {ref.split("-", 1)[0] for ref in refs}
        if "SC" not in kinds or not ({"CH", "T"} & kinds):
            diagnostics.append(
                Diagnostic(
                    "obligation.coverage",
                    "Each obligation must cover at least one SC and one CH or T.",
                    f"Expand {record.id}.covered_by.",
                    record.id,
                    line=record.line,
                )
            )
        if any(ref.split("-", 1)[0] == "RQ" for ref in refs):
            diagnostics.append(
                Diagnostic(
                    "obligation.coverage",
                    "Obligation coverage cannot reference other RQ records.",
                    f"Remove RQ references from {record.id}.covered_by.",
                    record.id,
                    line=record.line,
                )
            )
        category = record.fields.get("category", "")
        if "category" in record.fields and category not in RQ_CATEGORIES:
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    "Obligation category is unsupported.",
                    f"Correct {record.id}.category.",
                    record.id,
                    line=record.line,
                )
            )
        if source in RQ_REQUIRED_CATEGORIES and not category:
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    f"Typed {source} obligations require category.",
                    f"Set {record.id}.category to a required {source} category.",
                    record.id,
                    line=record.line,
                )
            )
    kind = request_source.get("kind") if isinstance(request_source, dict) else None
    if kind in RQ_SOURCES:
        matching = [record for record in obligations if record.fields.get("source") == kind]
        if not matching:
            diagnostics.append(
                Diagnostic(
                    "obligation.source",
                    f"Typed {kind} handoffs require at least one RQ with source: {kind}.",
                    f"Add an RQ record with source: {kind}.",
                )
            )
        required_categories = RQ_REQUIRED_CATEGORIES.get(kind)
        if required_categories is not None and matching:
            present = {record.fields.get("category", "") for record in matching}
            missing = sorted(required_categories - present)
            if missing:
                diagnostics.append(
                    Diagnostic(
                        "obligation.coverage",
                        f"Typed {kind} handoffs require RQ categories: {', '.join(sorted(required_categories))}.",
                        f"Add RQ records for missing categories: {', '.join(missing)}.",
                    )
                )
        if kind in {"audit", "design", "optimization", "issue"} and request_text and matching:
            selected_body = _selected_handoff_material(kind, request_text, request_source)
            if not selected_body.strip():
                diagnostics.append(
                    Diagnostic(
                        "obligation.anchor",
                        f"Selected {kind} handoff material is absent from the request body.",
                        f"Use a plan-ready {kind} handoff with stable selected sections.",
                    )
                )
            else:
                for record in matching:
                    anchor = record.fields.get("anchor", "")
                    if anchor and anchor not in selected_body:
                        diagnostics.append(
                            Diagnostic(
                                "obligation.anchor",
                                f"Obligation anchor is outside selected {kind} handoff material.",
                                f"Copy exact selected {kind} text into {record.id}.anchor.",
                                record.id,
                                line=record.line,
                            )
                        )
        shape_patterns = {
            "design": re.compile(r"\b(?:boundary|interface|decision|contract|seam)\b", re.I),
            "optimization": re.compile(
                r"\b(?:candidate|measure|workflow|latency|throughput|p95|cache|performance)\b",
                re.I,
            ),
            "issue": re.compile(r"\b(?:protect\w*|constraint|outcome|preserve|must)\b", re.I),
        }
        pattern = shape_patterns.get(kind)
        if pattern is not None and matching and not any(pattern.search(record.fields.get("obligation", "")) for record in matching):
            diagnostics.append(
                Diagnostic(
                    "obligation.shape",
                    f"{kind.title()} handoff obligations must name the inherited {kind} material.",
                    f"Tighten the {kind} RQ obligation text.",
                    matching[0].id,
                    line=matching[0].line,
                )
            )
    if kind == "generic" and request_bytes is not None and request_text:
        for record in obligations:
            source = record.fields.get("source", "")
            if source != "request":
                diagnostics.append(
                    Diagnostic(
                        "obligation.source",
                        "Generic requests require RQ.source: request.",
                        f"Set {record.id}.source to request.",
                        record.id,
                        line=record.line,
                    )
                )
            anchor = record.fields.get("anchor", "")
            if _is_weak_anchor(anchor):
                diagnostics.append(
                    Diagnostic(
                        "obligation.anchor",
                        "Obligation anchor is weak or trivial.",
                        f"Set {record.id}.anchor to material request text that identifies the obligation.",
                        record.id,
                        line=record.line,
                    )
                )
        request_rqs = [record for record in obligations if record.fields.get("source") == "request"]
        items = extract_structured_request_items(request_text)
        anchor_items: dict[str, set[str]] = defaultdict(set)
        for item in items:
            covering = [
                record
                for record in request_rqs
                if (anchor := record.fields.get("anchor", ""))
                and not _is_weak_anchor(anchor)
                and anchor in item
            ]
            if not covering:
                preview = item if len(item) <= 96 else item[:93] + "..."
                diagnostics.append(
                    Diagnostic(
                        "obligation.coverage",
                        f"Structured request item is uncovered: {preview}",
                        "Add an RQ with source: request whose anchor is exact text from that item.",
                    )
                )
            for record in covering:
                anchor_items[record.fields.get("anchor", "")].add(item)
        for anchor, covered_items in sorted(anchor_items.items()):
            if len(covered_items) >= 2:
                diagnostics.append(
                    Diagnostic(
                        "obligation.anchor",
                        "The same obligation anchor cannot cover multiple structured request items.",
                        "Use a distinct material anchor for each normative request item.",
                    )
                )
    return diagnostics


def _bug_fix_regression_diagnostics(plan: Plan) -> list[Diagnostic]:
    if plan.metadata.get("intent") != "bug-fix":
        return []
    fail_before = re.compile(r"\b(?:fail(?:s|ed|ing)?\s+before|before\s+the\s+fix)\b", re.I)
    after_fix = re.compile(r"\b(?:pass(?:es|ed)?\s+after|after\s+the\s+fix)\b", re.I)
    for record in plan.records.get("T", ()):
        verification = " ".join(record.fields.get(field, "") for field in ("given", "when", "then"))
        if fail_before.search(verification) and after_fix.search(verification):
            return []
    return [
        Diagnostic(
            "verification.regression",
            "Bug-fix plans require one T record stating fail-before and after-fix pass expectations.",
            "Update a T-n given/when/then to require fail-before and after-the-fix coverage.",
        )
    ]


def _propagation_diagnostics(plan: Plan, repository: RepositoryView | None = None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    fact_ids = plan.ids("F")
    planned_paths = {
        change.fields.get("path", "").replace("\\", "/")
        for change in plan.records.get("CH", ())
        if change.fields.get("path")
    }
    new_paths = {
        change.fields.get("path", "").replace("\\", "/")
        for change in plan.records.get("CH", ())
        if change.fields.get("status") == "new" and change.fields.get("path")
    }
    for record in plan.records.get("P", ()):
        disposition = record.fields.get("disposition", "")
        path = record.fields.get("path", "").replace("\\", "/")
        reason = record.fields.get("reason", "")
        surface = record.fields.get("surface", "")
        reason_facts = {ref for ref in _refs(reason) if ref.split("-", 1)[0] == "F"}
        if surface not in PROPAGATION_SURFACES:
            diagnostics.append(
                Diagnostic(
                    "record.invalid",
                    "Propagation surface is unsupported.",
                    f"Correct {record.id}.surface to a documented surface token.",
                    record.id,
                    line=record.line,
                )
            )
        if disposition in {"unchanged", "out-of-scope"}:
            if not reason_facts or not reason_facts <= fact_ids or not _substantive(reason, 3):
                diagnostics.append(
                    Diagnostic(
                        "propagation.evidence",
                        "Unchanged/out-of-scope propagation must cite evidence and a concrete sweep conclusion.",
                        f"Update {record.id}.reason to cite F-n and describe the bounded sweep.",
                        record.id,
                        line=record.line,
                    )
                )
        elif disposition in {"changed", "test-only"}:
            exists = False
            if repository is not None and path:
                try:
                    repository.get(path)
                    exists = True
                except (FileNotFoundError, ValueError):
                    exists = False
            if path and not exists and path not in planned_paths and path not in new_paths:
                diagnostics.append(
                    Diagnostic(
                        "propagation.path",
                        "Changed/test-only propagation paths must exist or match a planned CH path.",
                        f"Correct {record.id}.path to a current or planned repository surface.",
                        record.id,
                        path,
                        line=record.line,
                    )
                )
            if not _substantive(reason, 2):
                diagnostics.append(
                    Diagnostic(
                        "propagation.evidence",
                        "Changed/test-only propagation needs a concrete reason.",
                        f"Update {record.id}.reason.",
                        record.id,
                        line=record.line,
                    )
                )
    owned_by_disposition: dict[str, set[str]] = {
        "local_declaration": set(),
        "any": set(),
        "distinct_or_no_impact": set(),
    }
    change_paths = {
        change.id: change.fields.get("path", "").replace("\\", "/")
        for change in plan.records.get("CH", ())
    }
    for record in plan.records.get("P", ()):
        owners = _refs(record.fields.get("owner", ""))
        owned_by_disposition["any"].update(owners)
        path = record.fields.get("path", "").replace("\\", "/")
        disposition = record.fields.get("disposition", "")
        if disposition in {"unchanged", "out-of-scope"} and {
            ref for ref in _refs(record.fields.get("reason", "")) if ref.split("-", 1)[0] == "F"
        } <= fact_ids and _substantive(record.fields.get("reason", ""), 3):
            owned_by_disposition["local_declaration"].update(owners)
            owned_by_disposition["distinct_or_no_impact"].update(owners)
        if disposition in {"changed", "test-only"}:
            for owner in owners:
                if path and path != change_paths.get(owner, ""):
                    owned_by_disposition["distinct_or_no_impact"].add(owner)
    for change in plan.records.get("CH", ()):
        locality = change.fields.get("locality")
        if locality == "shared" and change.id not in owned_by_disposition["any"]:
            diagnostics.append(
                Diagnostic(
                    "propagation.required",
                    "Shared changes require at least one matching Propagation record.",
                    f"Add a P-n owned by {change.id} or set locality to local/test-only.",
                    change.id,
                    line=change.line,
                )
            )
        if locality == "shared" and change.id not in owned_by_disposition["distinct_or_no_impact"]:
            diagnostics.append(
                Diagnostic(
                    "propagation.required",
                    "Shared changes require a distinct affected surface or evidence-backed no-impact declaration.",
                    f"Add a P-n owned by {change.id} with a path other than the CH path, or unchanged/out-of-scope citing F-n.",
                    change.id,
                    line=change.line,
                )
            )
        if (
            plan.tier != "tiny"
            and locality == "local"
            and change.id not in owned_by_disposition["local_declaration"]
        ):
            diagnostics.append(
                Diagnostic(
                    "propagation.required",
                    "Non-tiny local changes require an evidence-backed no-propagation declaration.",
                    f"Add a P-n owned by {change.id} with disposition unchanged or out-of-scope citing F-n.",
                    change.id,
                    line=change.line,
                )
            )
    return diagnostics


def _record_diagnostics(
    plan: Plan,
    request_bytes: bytes | None = None,
    request_source: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    all_ids = plan.ids()
    for kind in ("RQ", "SC", "F", "CH", "T"):
        if not plan.records.get(kind):
            diagnostics.append(Diagnostic("record.invalid", f"At least one {kind} record is required.", f"Add a concrete {kind}-1 record."))
    diagnostics.extend(_obligation_diagnostics(plan, request_bytes, request_source))
    diagnostics.extend(_bug_fix_regression_diagnostics(plan))
    for record in plan.all_records():
        kind = record.id.split("-", 1)[0]
        if record.section != RECORD_SECTIONS[kind]:
            diagnostics.append(Diagnostic("record.invalid", f"{record.id} is in the wrong section.", f"Move {record.id} to {RECORD_SECTIONS[kind]}.", record.id, line=record.line))
        missing = REQUIRED_FIELDS[kind] - set(record.fields)
        unknown = set(record.fields) - REQUIRED_FIELDS[kind] - OPTIONAL_FIELDS.get(kind, set())
        if missing or unknown:
            detail = f"missing={sorted(missing)}; unknown={sorted(unknown)}"
            diagnostics.append(Diagnostic("record.invalid", detail, f"Correct the fields on {record.id}.", record.id, line=record.line))
        for field, allowed in REFERENCE_FIELDS.get(kind, {}).items():
            raw = record.fields.get(field, "")
            if kind == "CH" and field == "depends_on" and DEPENDS_NONE_RE.fullmatch(raw.strip() or ""):
                continue
            refs = _refs(raw)
            if field in REQUIRED_FIELDS[kind] and not refs and not (kind == "CH" and field == "depends_on"):
                diagnostics.append(Diagnostic("reference.undefined", f"{record.id}.{field} requires typed references.", f"Add valid references to {record.id}.{field}.", record.id, line=record.line))
            for ref in refs:
                if ref not in all_ids or ref.split("-", 1)[0] not in allowed:
                    diagnostics.append(Diagnostic("reference.undefined", f"{record.id}.{field} references invalid {ref}.", f"Correct {record.id}.{field}.", record.id, line=record.line))
        for field, value in record.fields.items():
            if kind == "CH" and field == "depends_on":
                continue
            for ref in _refs(value) - all_ids:
                diagnostics.append(Diagnostic("reference.undefined", f"Unknown reference {ref}.", f"Correct the reference in {record.id}.", record.id, line=record.line))
        if kind == "SC" and not all(_substantive(record.fields.get(field, "")) for field in ("given", "when", "then", "unchanged")):
            diagnostics.append(Diagnostic("record.invalid", "Success criteria must be observable and concrete.", f"Make {record.id} given/when/then/unchanged observable.", record.id, line=record.line))
        if kind == "CH":
            if not _substantive(record.fields.get("change", ""), 5):
                diagnostics.append(Diagnostic("change.specificity", "Change behavior is not implementation-specific.", f"Describe exact behavior, ordering, errors, or side effects in {record.id}.", record.id, line=record.line))
            if record.fields.get("locality") not in LOCALITIES:
                diagnostics.append(Diagnostic("record.invalid", "Change locality must be local, shared, or test-only.", f"Correct {record.id}.locality.", record.id, line=record.line))
            if record.fields.get("reversibility") not in REVERSIBILITIES:
                diagnostics.append(Diagnostic("record.invalid", "Change reversibility must be reversible, conditional, or irreversible.", f"Correct {record.id}.reversibility.", record.id, line=record.line))
        if kind == "T" and (not all(_substantive(record.fields.get(field, "")) for field in ("given", "when", "then")) or not record.fields.get("command", "").strip()):
            diagnostics.append(Diagnostic("verification.specificity", "Verification must state observable behavior and a runnable command.", f"Correct {record.id}.", record.id, line=record.line))
        if kind == "P" and record.fields.get("disposition") not in {"changed", "test-only", "unchanged", "out-of-scope"}:
            diagnostics.append(Diagnostic("record.invalid", "Propagation disposition is unsupported.", f"Correct {record.id}.disposition.", record.id, line=record.line))
        if kind == "B" and record.fields.get("flow", "").count("->") < 2:
            diagnostics.append(Diagnostic("record.invalid", "Boundary flow requires at least three stages.", f"Correct {record.id}.flow.", record.id, line=record.line))
        if kind == "R" and record.fields.get("severity") not in {"P0", "P1", "P2"}:
            diagnostics.append(Diagnostic("record.invalid", "Risk severity must be P0, P1, or P2.", f"Correct {record.id}.severity.", record.id, line=record.line))
    ordered, dependency_diagnostics = topological_change_order(plan)
    diagnostics.extend(dependency_diagnostics)
    _ = ordered
    for change in plan.records.get("CH", ()):
        if change.fields.get("reversibility") == "irreversible":
            if plan.tier != "high-risk":
                diagnostics.append(
                    Diagnostic(
                        "change.irreversible",
                        "Irreversible changes require high-risk tier.",
                        f"Raise the plan tier or correct {change.id}.reversibility.",
                        change.id,
                        line=change.line,
                    )
                )
            if not plan.risk_domains:
                diagnostics.append(
                    Diagnostic(
                        "change.irreversible",
                        "Irreversible changes require at least one risk domain.",
                        "Declare the applicable risk domain.",
                        change.id,
                        line=change.line,
                    )
                )
            if not plan.records.get("B") or not plan.records.get("R"):
                diagnostics.append(
                    Diagnostic(
                        "change.irreversible",
                        "Irreversible changes require boundary and risk records.",
                        "Add owned B-n and R-n records.",
                        change.id,
                        line=change.line,
                    )
                )
            if "Rollout and Rollback" not in plan.sections:
                diagnostics.append(
                    Diagnostic(
                        "change.irreversible",
                        "Irreversible changes require Rollout and Rollback.",
                        "Add a concrete Rollout and Rollback section.",
                        change.id,
                        line=change.line,
                    )
                )
    if plan.tier == "high-risk" and (not plan.records.get("B") or not plan.records.get("R")):
        diagnostics.append(Diagnostic("record.invalid", "High-risk plans require boundary and risk records.", "Add owned B-n and R-n records."))
    if plan.risk_domains & ROLLOUT_DOMAINS and "Rollout and Rollback" not in plan.sections:
        diagnostics.append(Diagnostic("section.order", "Declared risk domains require Rollout and Rollback.", "Add a concrete Rollout and Rollback section."))
    covered = set().union(*(_refs(record.fields.get("covers", "")) for record in plan.records.get("T", ())), set())
    for identifier in sorted((plan.ids("SC") | plan.ids("CH")) - covered):
        diagnostics.append(Diagnostic("verification.coverage", f"{identifier} is not covered by verification.", f"Add {identifier} to a T-n covers field.", identifier))
    return diagnostics


def _excerpt(entry: RepositoryFile, raw_range: str) -> tuple[int, int, str]:
    try:
        start_text, end_text = raw_range.split("-", 1)
        start, end = int(start_text), int(end_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError("lines must be start-end") from exc
    if start < 1 or end < start or end > len(entry.lines):
        raise ValueError("lines are outside the file")
    return start, end, "\n".join(entry.lines[start - 1 : end]) + "\n"


def _node_in_range(node: ast.AST, start: int, end: int) -> bool:
    node_start = getattr(node, "lineno", 0)
    node_end = getattr(node, "end_lineno", node_start)
    return start <= node_start <= end and node_end <= end


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _tree_text(entry: RepositoryFile, node: Any) -> str:
    return entry.data[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _tree_field_text(entry: RepositoryFile, node: Any, *names: str) -> str:
    for name in names:
        value = node.child_by_field_name(name)
        if value is not None:
            return _tree_text(entry, value).strip()
    return ""


def _tree_nodes_in_range(tree: Any, start: int, end: int) -> list[Any]:
    result: list[Any] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        node_start = node.start_point.row + 1
        node_end = node.end_point.row + 1
        if start <= node_start and node_end <= end:
            result.append(node)
        stack.extend(reversed(node.named_children))
    return result


def _normalized_structure(value: str) -> str:
    return re.sub(r"\s+", "", value).strip("()[]{}:;")


def _tree_structured(
    record: Record,
    entry: RepositoryFile,
    tree: Any,
    start: int,
    end: int,
) -> str | None:
    kind = record.fields["kind"]
    nodes = _tree_nodes_in_range(tree, start, end)
    function_types = {
        "function_declaration",
        "function_definition",
        "function_item",
        "method",
        "method_declaration",
        "method_definition",
        "singleton_method",
    }
    class_types = {
        "class_declaration",
        "class_definition",
        "interface_declaration",
        "object_declaration",
        "struct_item",
    }
    call_types = {"call", "call_expression", "method_invocation"}
    branch_types = {
        "conditional_expression",
        "if_expression",
        "if_statement",
        "match_expression",
        "when_expression",
        "while_expression",
        "while_statement",
    }
    error_types = {
        "catch_clause",
        "except_clause",
        "raise_statement",
        "rescue",
        "throw_expression",
        "throw_statement",
    }
    side_effect_types = {
        "assignment",
        "assignment_expression",
        "augmented_assignment",
        "call",
        "call_expression",
        "method_invocation",
        "update_expression",
    }

    if kind == "function-signature":
        for node in nodes:
            if node.type not in function_types:
                continue
            name = _tree_field_text(entry, node, "name")
            if name not in record.fields["anchor"]:
                continue
            parameters = _tree_field_text(entry, node, "parameters", "parameter")
            returns = _tree_field_text(entry, node, "return_type", "type") or "none"
            prefix = _tree_text(entry, node).split(name, 1)[0]
            actual_async = str(bool(re.search(r"\basync\b", prefix))).lower()
            if (
                _normalized_structure(parameters) == _normalized_structure(record.fields["parameters"])
                and _normalized_structure(returns) == _normalized_structure(record.fields["returns"])
                and actual_async == record.fields["async"].lower()
            ):
                return None
        return "function parameters, return annotation, or async value does not match"
    if kind == "class-signature":
        expected = _normalized_structure(record.fields["bases"])
        for node in nodes:
            if node.type not in class_types or _tree_field_text(entry, node, "name") not in record.fields["anchor"]:
                continue
            bases = _tree_field_text(
                entry,
                node,
                "superclasses",
                "superclass",
                "interfaces",
                "delegation_specifiers",
            )
            if _normalized_structure(bases) == expected:
                return None
        return "class bases do not match"
    if kind in {"call-edge", "external-call"}:
        for node in nodes:
            if node.type not in call_types:
                continue
            callee = _tree_field_text(entry, node, "function", "method", "name")
            if not (callee == record.fields["callee"] or callee.endswith("." + record.fields["callee"])):
                continue
            if kind == "external-call":
                return None
            parent = node.parent
            while parent is not None and parent.type not in function_types:
                parent = parent.parent
            if parent is not None and _tree_field_text(entry, parent, "name") == record.fields["caller"]:
                return None
        return "call edge is absent from the cited range"
    if kind == "branch":
        expected = _normalized_structure(record.fields["condition"])
        for node in nodes:
            if node.type in branch_types:
                condition = _tree_field_text(entry, node, "condition", "value")
                if _normalized_structure(condition) == expected:
                    return None
        return "branch condition does not match"
    if kind == "error":
        expected = record.fields["error"]
        if any(node.type in error_types and re.search(rf"\b{re.escape(expected)}\b", _tree_text(entry, node)) for node in nodes):
            return None
        return "error type is absent from the cited range"
    if kind == "side-effect":
        effect = record.fields["effect"]
        if any(node.type in side_effect_types and effect in _tree_text(entry, node) for node in nodes):
            return None
        return "side effect is absent from the cited range"
    return "structured evidence kind has no exact validator for this grammar"


def _python_structured(record: Record, view: RepositoryView, start: int, end: int) -> str | None:
    kind, path = record.fields["kind"], record.fields["path"]
    try:
        tree = view.parse_python(path)
    except SyntaxError:
        return "cited Python file cannot be parsed"
    nodes = [node for node in ast.walk(tree) if _node_in_range(node, start, end)]
    if kind == "function-signature":
        functions = [node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in record.fields["anchor"]]
        if not functions:
            return "function signature is absent from the cited range"
        function_node = functions[0]
        parameters = ",".join(arg.arg for arg in (*function_node.args.posonlyargs, *function_node.args.args, *function_node.args.kwonlyargs))
        expected_async = str(isinstance(function_node, ast.AsyncFunctionDef)).lower()
        returns = ast.unparse(function_node.returns) if function_node.returns else "none"
        if parameters != record.fields["parameters"].replace(" ", "") or returns != record.fields["returns"] or expected_async != record.fields["async"].lower():
            return "function parameters, return annotation, or async value does not match"
    elif kind == "class-signature":
        classes = [node for node in nodes if isinstance(node, ast.ClassDef) and node.name in record.fields["anchor"]]
        if not classes or ",".join(ast.unparse(base) for base in classes[0].bases) != record.fields["bases"].replace(" ", ""):
            return "class bases do not match"
    elif kind in {"call-edge", "external-call"}:
        callee = record.fields["callee"]
        calls = [_dotted_name(node.func) for node in nodes if isinstance(node, ast.Call)]
        if callee not in calls and not any(value.endswith("." + callee) for value in calls):
            return "callee is absent from calls in the cited range"
        if kind == "call-edge" and not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == record.fields["caller"] for node in nodes):
            return "caller is absent from the cited range"
    elif kind == "branch":
        conditions = [ast.unparse(node.test) for node in nodes if isinstance(node, (ast.If, ast.While, ast.IfExp))]
        if record.fields["condition"] not in conditions:
            return "branch condition does not match"
    elif kind == "error":
        names = []
        for node in nodes:
            if isinstance(node, ast.Raise) and node.exc is not None:
                names.append(_dotted_name(node.exc.func) if isinstance(node.exc, ast.Call) else _dotted_name(node.exc))
            elif isinstance(node, ast.ExceptHandler) and node.type is not None:
                names.append(_dotted_name(node.type))
        if record.fields["error"] not in names:
            return "error type is absent from the cited range"
    elif kind == "side-effect" and record.fields["effect"] not in "\n".join(view.get(path).lines[start - 1 : end]):
        return "side-effect anchor is absent"
    return None


def _structured_fact(
    record: Record,
    view: RepositoryView,
    entry: RepositoryFile,
    start: int,
    end: int,
    excerpt: str,
) -> tuple[str, str | None, str | None]:
    kind = record.fields["kind"]
    if kind == "source":
        return "source", None, None
    if entry.path.suffix.lower() == ".py" and kind in {"function-signature", "class-signature", "call-edge", "external-call", "branch", "error", "side-effect"}:
        return kind, _python_structured(record, view, start, end), None
    if kind == "schema-shape":
        try:
            value = json.loads(entry.text)
        except json.JSONDecodeError:
            return kind, "schema-shape requires valid JSON", None
        expected = {field.strip() for field in record.fields["fields"].split(",") if field.strip()}
        actual = set(value) if isinstance(value, dict) else set()
        return kind, None if expected <= actual else "schema fields are absent", None
    if kind == "config-key":
        key, value = record.fields["key"], record.fields["value"]
        return kind, None if key in entry.text and value in entry.text else "config key or value is absent", None
    if kind == "generated-from":
        generator, output = record.fields["generator"], record.fields["output"]
        try:
            generator_entry = view.get(generator)
        except (ValueError, FileNotFoundError):
            return kind, "generator path is invalid or absent", None
        return kind, None if output in generator_entry.text else "generator does not name the output", None
    if kind == "directory-ownership":
        directory = record.fields["directory"].rstrip("/")
        try:
            view.resolve(directory)
        except ValueError:
            return kind, "owned directory escapes the repository", None
        return (
            kind,
            None if entry.relative.startswith(directory + "/") or entry.relative == directory else "evidence file is outside the owned directory",
            None,
        )
    tree, available = view.parse_tree(record.fields["path"])
    if not available:
        grammar = TREE_SITTER_GRAMMARS.get(entry.path.suffix.lower())
        package = grammar[0] if grammar else None
        detail = f"structured validator is unavailable for {entry.path.suffix.lower() or 'this file type'}"
        action = f"Change {record.id}.kind to source"
        if package:
            action += f" or install the optional {package} grammar"
        return kind, detail, action + "."
    return kind, _tree_structured(record, entry, tree, start, end), None


def _fact_diagnostics(plan: Plan, view: RepositoryView) -> tuple[list[Diagnostic], list[dict[str, str]]]:
    diagnostics: list[Diagnostic] = []
    proofs: list[dict[str, str]] = []
    facts = {record.id: record for record in plan.records.get("F", ())}
    for fact in facts.values():
        kind = fact.fields.get("kind", "")
        path = fact.fields.get("path", "")
        if kind not in FACT_FIELDS:
            diagnostics.append(Diagnostic("fact.structured", "Evidence kind is unsupported.", f"Correct {fact.id}.kind.", fact.id, path, fact.line))
            continue
        expected_fields = REQUIRED_FIELDS["F"] | FACT_FIELDS[kind]
        if set(fact.fields) != expected_fields:
            diagnostics.append(Diagnostic("record.invalid", "Evidence fields do not match its kind.", f"Correct the fields on {fact.id}.", fact.id, path, fact.line))
            continue
        try:
            entry = view.get(path)
        except (ValueError, FileNotFoundError) as exc:
            diagnostics.append(Diagnostic("fact.path", str(exc), f"Correct {fact.id}.path.", fact.id, path, fact.line, "missing_evidence"))
            continue
        try:
            start, end, excerpt = _excerpt(entry, fact.fields["lines"])
        except ValueError as exc:
            diagnostics.append(Diagnostic("fact.lines", str(exc), f"Correct {fact.id}.lines.", fact.id, path, fact.line, "stale_evidence"))
            continue
        if fact.fields["anchor"] not in excerpt:
            diagnostics.append(Diagnostic("fact.anchor", "Anchor is absent from the cited range.", f"Correct {fact.id} lines or anchor.", fact.id, path, fact.line, "stale_evidence"))
            continue
        verified_kind, error, required_action = _structured_fact(fact, view, entry, start, end, excerpt)
        if error:
            diagnostics.append(
                Diagnostic(
                    "fact.structured",
                    error,
                    required_action or f"Correct the structured fields or range for {fact.id}.",
                    fact.id,
                    path,
                    fact.line,
                    "stale_evidence",
                )
            )
            continue
        proofs.append(
            {
                "fact_id": fact.id,
                "path": entry.relative,
                "lines": fact.fields["lines"],
                "anchor": fact.fields["anchor"],
                "file_sha256": view.digest(path),
                "excerpt_sha256": _sha256(excerpt.encode("utf-8")),
                "verified_kind": verified_kind,
            }
        )
    return diagnostics, proofs


def _change_diagnostics(plan: Plan, view: RepositoryView) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    facts = {record.id: record for record in plan.records.get("F", ())}
    changes = {record.id: record for record in plan.records.get("CH", ())}

    def owner_facts(identifier: str, seen: frozenset[str] = frozenset()) -> set[str]:
        if identifier in seen:
            return set()
        if identifier in facts:
            return {identifier}
        owner_change = changes.get(identifier)
        if owner_change is None:
            return set()
        roots: set[str] = set()
        for parent in _refs(owner_change.fields.get("owner", "")):
            roots.update(owner_facts(parent, seen | {identifier}))
        return roots

    def fact_owns_path(fact: Record, target: str) -> bool:
        normalized_target = target.replace("\\", "/")
        if fact.fields.get("kind") == "directory-ownership":
            directory = fact.fields.get("directory", "").replace("\\", "/").rstrip("/")
            return bool(directory) and normalized_target.startswith(directory + "/")
        if fact.fields.get("kind") == "generated-from":
            return fact.fields.get("output", "").replace("\\", "/") == normalized_target
        return False

    for change in changes.values():
        status, raw_path = change.fields.get("status"), change.fields.get("path", "")
        if status not in {"existing", "new"}:
            diagnostics.append(Diagnostic("change.target", "Status must be existing or new.", f"Correct {change.id}.status.", change.id, raw_path, change.line))
            continue
        try:
            path = view.resolve(raw_path)
        except ValueError as exc:
            diagnostics.append(Diagnostic("change.target", str(exc), f"Correct {change.id}.path.", change.id, raw_path, change.line))
            continue
        evidence_refs = _refs(change.fields.get("evidence", ""))
        if status == "existing":
            try:
                entry = view.get(raw_path)
            except FileNotFoundError:
                diagnostics.append(Diagnostic("change.target", "Existing change target is absent.", f"Correct {change.id}.path or status.", change.id, raw_path, change.line))
                continue
            same_path = [facts[ref] for ref in evidence_refs if ref in facts and facts[ref].fields.get("path", "").replace("\\", "/") == entry.relative]
            if not same_path:
                diagnostics.append(Diagnostic("change.evidence", "Existing change lacks same-path evidence.", f"Reference a same-path F-n from {change.id}.evidence.", change.id, raw_path, change.line))
            elif change.fields.get("anchor", "") not in entry.text:
                diagnostics.append(Diagnostic("change.target", "Change anchor is absent from the target.", f"Correct {change.id}.anchor.", change.id, raw_path, change.line))
        else:
            owners = _refs(change.fields.get("owner", ""))
            if path.exists() or not owners:
                diagnostics.append(Diagnostic("change.target", "New target must be absent and have an owner reference.", f"Correct {change.id}.path or owner.", change.id, raw_path, change.line))
            roots_by_owner = {owner: owner_facts(owner) for owner in owners}
            if owners and (
                any(not roots for roots in roots_by_owner.values())
                or not any(fact_owns_path(facts[root], raw_path) for roots in roots_by_owner.values() for root in roots)
            ):
                diagnostics.append(
                    Diagnostic(
                        "change.evidence",
                        "New target ownership must resolve without cycles to a directory or generator fact that owns the exact path.",
                        f"Correct {change.id}.owner or its ownership chain.",
                        change.id,
                        raw_path,
                        change.line,
                    )
                )
    return diagnostics


def validate_draft(
    text: str,
    repo_root: Path,
    *,
    view: RepositoryView | None = None,
    request_bytes: bytes | None = None,
    request_source: dict[str, Any] | None = None,
    handoff_item: str | None = None,
) -> ValidationResult:
    repository = view or RepositoryView(repo_root)
    plan, diagnostics = parse_plan(text)
    proofs: list[dict[str, str]] = []
    if plan is None:
        return ValidationResult(None, tuple(diagnostics), (), repository)
    if diagnostics:
        diagnostics.sort(key=lambda item: (item.line is None, item.line or 0, item.code, item.record or ""))
        return ValidationResult(plan, tuple(diagnostics), (), repository)
    resolved_source = request_source
    if resolved_source is None and request_bytes is not None:
        try:
            resolved_source = detect_request_source(request_bytes, handoff_item)
        except ValueError:
            resolved_source = None
    diagnostics.extend(_metadata_diagnostics(plan))
    diagnostics.extend(_record_diagnostics(plan, request_bytes, resolved_source))
    if not diagnostics:
        fact_diagnostics, proofs = _fact_diagnostics(plan, repository)
        diagnostics.extend(fact_diagnostics)
        if not fact_diagnostics:
            diagnostics.extend(_change_diagnostics(plan, repository))
    diagnostics.extend(_propagation_diagnostics(plan, repository))
    diagnostics.sort(key=lambda item: (item.line is None, item.line or 0, item.code, item.record or ""))
    return ValidationResult(plan, tuple(diagnostics), tuple(sorted(proofs, key=lambda item: item["fact_id"])), repository)


def canonical_body(text: str) -> str:
    lines = [
        line.rstrip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if not line.startswith("<!-- plan-proof:") and not line.startswith("<!-- plan-validation:")
    ]
    return "\n".join(lines).rstrip() + "\n"


def _intake_error(code: str, message: str) -> ValueError:
    error = ValueError(message)
    setattr(
        error,
        "diagnostics",
        (Diagnostic(code, message, "Repair or replace the request handoff and rerun the same seal command."),),
    )
    return error


def detect_request_source(request_bytes: bytes, handoff_item: str | None = None) -> dict[str, Any]:
    """Verify a typed handoff envelope and return its proof binding."""
    try:
        text = request_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _intake_error("request.encoding", "Request files must be valid UTF-8.") from exc
    first, separator, body = text.partition("\n")
    match = HANDOFF_RECEIPT_RE.fullmatch(first.rstrip("\r"))
    if match is None:
        if handoff_item is not None:
            raise _intake_error("handoff.item.unexpected", "handoff_item is valid only for audit handoffs.")
        if HANDOFF_LIKE_RE.fullmatch(first.rstrip("\r")):
            raise _intake_error("handoff.marker.unsupported", "The request uses an unknown or unsupported handoff marker.")
        return {"kind": "generic", "contract_version": None, "item": None}
    if not separator:
        raise _intake_error("handoff.receipt.malformed", "Typed handoff content is missing after its receipt.")
    kind = match.group("kind")
    version = int(match.group("version"))
    if version != 1:
        raise _intake_error("handoff.version.unsupported", f"Unsupported {kind} handoff contract version {version}.")
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != match.group("digest"):
        raise _intake_error("handoff.receipt.stale", "Typed handoff receipt does not match its content.")
    if kind != "audit" and handoff_item is not None:
        raise _intake_error("handoff.item.unexpected", "handoff_item is valid only for audit handoffs.")
    selected: str | None = None
    if kind == "audit":
        findings = re.findall(r"^## Issue (?P<id>\S+)\s*$", body, re.MULTILINE)
        if not findings:
            raise _intake_error("handoff.audit.empty", "Audit handoff has no accepted findings to plan.")
        if handoff_item is None and len(findings) > 1:
            raise _intake_error("handoff.item.required", "Multi-finding audit handoffs require one handoff_item finding ID.")
        selected = handoff_item or findings[0]
        if selected not in findings:
            raise _intake_error("handoff.item.unknown", f"Audit handoff does not contain finding {selected!r}.")
    elif kind == "optimization":
        states = [item.strip() for item in re.findall(r"^- H-\d+:[^\n]*\bnext:\s*([^|\n]+)", body, re.MULTILINE)]
        if states != ["plan-ready"]:
            raise _intake_error("handoff.not_actionable", "Optimization handoff must have exactly one plan-ready state.")
    elif kind == "issue":
        metadata_match = re.search(r"<!-- issue-handoff-metadata -->\s*```json\s*(\{.*?\})\s*```", body, re.DOTALL)
        try:
            metadata = json.loads(metadata_match.group(1)) if metadata_match else {}
        except json.JSONDecodeError as exc:
            raise _intake_error("handoff.issue.metadata", "Issue handoff metadata is malformed.") from exc
        if metadata.get("status") != "plan-ready":
            raise _intake_error("handoff.not_actionable", "Issue handoff status must be plan-ready.")
    return {"kind": kind, "contract_version": version, "item": selected}


def build_proof_bundle(
    plan: Plan,
    view: RepositoryView,
    request_bytes: bytes,
    fact_proofs: Iterable[dict[str, str]],
    request_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    roles: dict[str, set[str]] = defaultdict(set)
    for fact in plan.records.get("F", ()):
        roles[fact.fields["path"].replace("\\", "/")].add("evidence")
        if fact.fields["kind"] == "generated-from":
            roles[fact.fields["generator"].replace("\\", "/")].add("generator")
        if fact.fields["kind"] == "config-key":
            roles[fact.fields["path"].replace("\\", "/")].add("config")
        if fact.fields["kind"] == "schema-shape":
            roles[fact.fields["path"].replace("\\", "/")].add("schema")
    for change in plan.records.get("CH", ()):
        if change.fields.get("status") == "existing":
            roles[change.fields["path"].replace("\\", "/")].add("target")
    files = [
        {"path": path, "sha256": view.digest(path), "roles": sorted(path_roles)}
        for path, path_roles in sorted(roles.items())
    ]
    identity, head = view.repository_identity()
    body = canonical_body(plan.text)
    obligation_anchors = [
        {
            "record": record.id,
            "source": record.fields.get("source", ""),
            "anchor_sha256": _sha256(record.fields.get("anchor", "").encode("utf-8")),
            "covered_by": sorted(_refs(record.fields.get("covered_by", "")), key=_change_id_sort_key),
        }
        for record in plan.records.get("RQ", ())
    ]
    change_order, _diagnostics = topological_change_order(plan)
    proof = {
        "version": 7,
        "facts": list(fact_proofs),
        "obligations": obligation_anchors,
        "change_order": change_order,
        "binding": {
            "repository_id": identity,
            "git_head": head,
            "request_sha256": _sha256(request_bytes),
            "plan_body_sha256": _sha256(body.encode("utf-8")),
            "files": files,
        },
    }
    if request_source is not None:
        proof["request"] = request_source
    else:
        proof["request"] = {"kind": "generic", "contract_version": None, "item": None}
    return proof


def render_sealed_plan(text: str, proof: dict[str, Any]) -> str:
    body = canonical_body(text)
    proof_json = _canonical_json(proof)
    proof_hash = _sha256(proof_json.encode("utf-8"))
    body_hash = _sha256(body.encode("utf-8"))
    lines = body.rstrip("\n").splitlines()
    metadata_index = next(index for index, line in enumerate(lines) if line.startswith("<!-- plan-metadata:"))
    lines[metadata_index + 1 : metadata_index + 1] = [
        f"<!-- plan-proof: {proof_json} -->",
        f"<!-- plan-validation: 7; body-sha256: {body_hash}; proof-sha256: {proof_hash} -->",
    ]
    return "\n".join(lines) + "\n"


def seal_plan(
    repo_root: Path,
    request_file: Path,
    draft_file: Path,
    *,
    handoff_item: str | None = None,
) -> SealResult:
    root = repo_root.resolve()
    request = request_file.resolve()
    draft = draft_file.resolve()
    if not request.is_file() or not draft.is_file():
        raise ValueError("request_file and draft_file must be existing files")
    request_bytes = request.read_bytes()
    request_source = detect_request_source(request_bytes, handoff_item)
    draft_text = draft.read_text(encoding="utf-8")
    result = validate_draft(
        draft_text,
        root,
        request_bytes=request_bytes,
        request_source=request_source,
        handoff_item=handoff_item,
    )
    if not result.valid or result.plan is None:
        error = ValueError("draft validation failed")
        setattr(error, "diagnostics", result.diagnostics)
        raise error
    proof = build_proof_bundle(result.plan, result.view, request_bytes, result.fact_proofs, request_source)
    sealed = render_sealed_plan(draft_text, proof)
    return SealResult(sealed, proof, result.view.counters())


def verify_sealed_plan(text: str, repo_root: Path, *, request_bytes: bytes | None = None) -> tuple[Plan | None, list[Diagnostic], RepositoryView]:
    view = RepositoryView(repo_root)
    proof_matches = list(PROOF_RE.finditer(text))
    validation_matches = list(VALIDATION_RE.finditer(text))
    diagnostics: list[Diagnostic] = []
    if len(proof_matches) != 1 or len(validation_matches) != 1:
        return None, [Diagnostic("proof.stale", "Sealed proof or receipt marker is missing.", "Use the exact output from seal_plan.py.", category="stale_evidence")], view
    try:
        proof = json.loads(proof_matches[0].group("json"))
        if not isinstance(proof, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        return None, [Diagnostic("proof.stale", "Plan proof is malformed.", "Use the exact output from seal_plan.py.", category="stale_evidence")], view
    receipt = validation_matches[0]
    body = canonical_body(text)
    if receipt.group("body") != _sha256(body.encode("utf-8")) or receipt.group("proof") != _sha256(_canonical_json(proof).encode("utf-8")):
        diagnostics.append(Diagnostic("proof.stale", "Plan body or proof digest does not match the receipt.", "Reseal the unchanged draft.", category="stale_evidence"))
    request_source = proof.get("request")
    validation = validate_draft(
        body,
        repo_root,
        view=view,
        request_bytes=request_bytes,
        request_source=request_source if isinstance(request_source, dict) else None,
        handoff_item=(
            request_source.get("item")
            if isinstance(request_source, dict) and isinstance(request_source.get("item"), str)
            else None
        ),
    )
    diagnostics.extend(validation.diagnostics)
    binding = proof.get("binding")
    binding_fields = binding if isinstance(binding, dict) else {}
    enriched_shape = set(proof) == {"version", "facts", "obligations", "change_order", "binding", "request"}
    request_shape_valid = (
        enriched_shape
        and isinstance(request_source, dict)
        and set(request_source) == {"kind", "contract_version", "item"}
        and request_source.get("kind") in {"generic", "audit", "design", "optimization", "issue"}
        and (request_source.get("contract_version") is None or request_source.get("contract_version") == 1)
        and (request_source.get("item") is None or isinstance(request_source.get("item"), str))
    )
    proof_shape_valid = (
        request_shape_valid
        and proof.get("version") == CONTRACT_VERSION
        and isinstance(proof.get("facts"), list)
        and isinstance(proof.get("obligations"), list)
        and isinstance(proof.get("change_order"), list)
        and isinstance(binding, dict)
        and set(binding) == {
            "repository_id",
            "git_head",
            "request_sha256",
            "plan_body_sha256",
            "files",
        }
        and isinstance(binding.get("repository_id"), str)
        and (binding.get("git_head") is None or isinstance(binding.get("git_head"), str))
        and isinstance(binding.get("request_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", binding.get("request_sha256", "")) is not None
        and isinstance(binding.get("files"), list)
    )
    if validation.valid and validation.plan is not None:
        expected = build_proof_bundle(
            validation.plan,
            view,
            request_bytes or b"",
            validation.fact_proofs,
            request_source if isinstance(request_source, dict) else None,
        )
        expected_binding = expected["binding"]
        proof_matches_body = (
            proof_shape_valid
            and proof.get("facts") == expected["facts"]
            and proof.get("obligations") == expected["obligations"]
            and proof.get("change_order") == expected["change_order"]
            and binding_fields.get("repository_id") == expected_binding["repository_id"]
            and binding_fields.get("plan_body_sha256") == expected_binding["plan_body_sha256"]
            and binding_fields.get("files") == expected_binding["files"]
        )
        if not proof_matches_body:
            diagnostics.append(
                Diagnostic(
                    "proof.stale",
                    "Proof facts or bound files do not match the validated plan body and repository.",
                    "Use the exact output from seal_plan.py.",
                    category="stale_evidence",
                )
            )
        if proof_shape_valid and request_bytes is not None and binding_fields.get("request_sha256") != _sha256(request_bytes):
            diagnostics.append(Diagnostic("proof.stale", "Request digest changed.", "Use the request sealed with the plan.", category="stale_evidence"))
        if proof_shape_valid and request_bytes is not None:
            try:
                selected_item = request_source.get("item") if isinstance(request_source, dict) else None
                detected = detect_request_source(request_bytes, selected_item)
            except ValueError:
                detected = None
            if detected != request_source:
                diagnostics.append(Diagnostic("proof.stale", "Request handoff type, version, or selected item changed.", "Use the request sealed with the plan.", category="stale_evidence"))
        return (
            dataclasses.replace(
                validation.plan,
                binding=binding if isinstance(binding, dict) else None,
                receipt={"body": receipt.group("body"), "proof": receipt.group("proof")},
            ),
            diagnostics,
            view,
        )
    if not proof_shape_valid:
        diagnostics.append(
            Diagnostic(
                "proof.stale",
                "Plan proof has missing or unsupported fields.",
                "Use the exact output from seal_plan.py.",
                category="stale_evidence",
            )
        )
    return validation.plan, diagnostics, view
