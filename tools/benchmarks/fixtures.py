from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "benchmarks"
SCHEMA_PATH = BENCHMARK_ROOT / "schema" / "fixture-manifest.schema.json"
MANIFEST_ROOT = BENCHMARK_ROOT / "manifests"
REPOSITORY_ROOT = BENCHMARK_ROOT / "repos"
ORACLE_ROOT = BENCHMARK_ROOT / "oracles" / "map-codebase-v2"
V3_ORACLE_ROOT = BENCHMARK_ROOT / "oracles" / "map-codebase-v3"
KNOWN_ORACLES = {"python-test", "path-set", "ownership", "abstention", "scale"}
REQUIRED_REALISTIC_CATEGORIES = frozenset({"ownership", "constraint", "impact", "abstention", "decoy", "safety"})
TREE_HASH_ALGORITHM = "sha256-path-content-v1"
RUNTIME_ARTIFACT_DIRECTORIES = frozenset(
    {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
)


class BenchmarkError(ValueError):
    """Raised when benchmark data violates a safety or integrity contract."""


@dataclass(frozen=True, slots=True)
class FixtureFile:
    """One exact file in a canonical fixture tree."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class FixtureTree:
    """Versioned, path-and-content fixture identity."""

    algorithm: str
    sha256: str
    files: tuple[FixtureFile, ...]

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        *,
        source: str = "fixture tree",
    ) -> FixtureTree:
        algorithm = str(data.get("hash_algorithm", ""))
        if algorithm != TREE_HASH_ALGORITHM:
            raise BenchmarkError(f"{source}: unsupported tree hash algorithm {algorithm!r}")
        raw_files = data.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            raise BenchmarkError(f"{source}: canonical file inventory must not be empty")
        files: list[FixtureFile] = []
        for index, raw_file in enumerate(raw_files):
            if not isinstance(raw_file, Mapping):
                raise BenchmarkError(f"{source}: files[{index}] must be an object")
            relative = _relative_path(str(raw_file.get("path", "")), f"{source}.files[{index}].path")
            sha256 = str(raw_file.get("sha256", ""))
            if not re.fullmatch(r"[a-f0-9]{64}", sha256):
                raise BenchmarkError(f"{source}: invalid content hash for {relative}")
            files.append(FixtureFile(path=relative.as_posix(), sha256=sha256))
        paths = [item.path for item in files]
        if paths != sorted(paths):
            raise BenchmarkError(f"{source}: canonical file inventory must be sorted")
        if len(paths) != len(set(paths)):
            raise BenchmarkError(f"{source}: canonical file inventory contains duplicate paths")
        expected_digest = str(data.get("sha256", ""))
        actual_digest = _tree_digest(files)
        if expected_digest != actual_digest:
            raise BenchmarkError(
                f"{source}: stale aggregate tree hash "
                f"(expected {expected_digest}, inventory {actual_digest})"
            )
        return cls(algorithm=algorithm, sha256=expected_digest, files=tuple(files))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "hash_algorithm": self.algorithm,
            "sha256": self.sha256,
            "files": [
                {"path": item.path, "sha256": item.sha256}
                for item in self.files
            ],
        }


def _relative_path(value: str, field: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise BenchmarkError(f"{field} must be a contained relative path: {value!r}")
    if ":" in path.parts[0] or "\\" in value:
        raise BenchmarkError(f"{field} must use portable POSIX path syntax: {value!r}")
    return path


def _contained(root: Path, relative: PurePosixPath) -> Path:
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise BenchmarkError(f"path escapes fixture root: {relative}") from exc
    return candidate


def _tree_digest(files: Iterable[FixtureFile]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(item.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(item.sha256))
        digest.update(b"\0")
    return digest.hexdigest()


def _is_runtime_artifact(relative: Path) -> bool:
    return any(part in RUNTIME_ARTIFACT_DIRECTORIES for part in relative.parts)


def inspect_fixture_tree(root: Path, *, allow_empty: bool = False) -> FixtureTree:
    """Inspect exact fixture bytes while excluding only central runtime artifacts."""
    if not root.is_dir():
        raise BenchmarkError(f"fixture repository does not exist: {root}")
    files: list[FixtureFile] = []
    candidates = sorted(
        root.rglob("*"),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    for path in candidates:
        relative = path.relative_to(root)
        if _is_runtime_artifact(relative):
            continue
        if path.is_symlink():
            raise BenchmarkError(f"fixture trees may not contain symlinks: {relative.as_posix()}")
        if not path.is_file():
            continue
        files.append(
            FixtureFile(
                path=relative.as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    if not files and not allow_empty:
        raise BenchmarkError(f"fixture repository is empty: {root}")
    return FixtureTree(
        algorithm=TREE_HASH_ALGORITHM,
        sha256=_tree_digest(files),
        files=tuple(files),
    )


def verify_fixture_tree(root: Path, expected: FixtureTree) -> None:
    """Fail closed when source bytes differ from a canonical fixture inventory."""
    actual = inspect_fixture_tree(root)
    expected_by_path = {item.path: item.sha256 for item in expected.files}
    actual_by_path = {item.path: item.sha256 for item in actual.files}
    missing = sorted(set(expected_by_path) - set(actual_by_path))
    if missing:
        raise BenchmarkError(f"fixture tree is missing declared path: {missing[0]}")
    unexpected = sorted(set(actual_by_path) - set(expected_by_path))
    if unexpected:
        raise BenchmarkError(f"fixture tree contains unexpected source path: {unexpected[0]}")
    for path, expected_hash in expected_by_path.items():
        if actual_by_path[path] != expected_hash:
            raise BenchmarkError(f"fixture tree content hash mismatch: {path}")
    if actual.sha256 != expected.sha256:
        raise BenchmarkError(
            f"fixture tree digest mismatch (expected {expected.sha256}, actual {actual.sha256})"
        )


def repository_digest(root: Path) -> str:
    """Compatibility wrapper for callers that need only the canonical digest."""
    return inspect_fixture_tree(root).sha256


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meaningful_file_count(root: Path, tree: FixtureTree | None = None) -> int:
    inventory = tree or inspect_fixture_tree(root)
    return sum(
        1
        for item in inventory.files
        if PurePosixPath(item.path).name not in {"__init__.py", ".gitattributes"}
        and "generated" not in PurePosixPath(item.path).parts
        and not PurePosixPath(item.path).name.startswith(
            ("component_", "check_component_", "service-")
        )
    )


def validate_manifest(data: dict[str, Any], *, source: Path | None = None) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise BenchmarkError(f"{source or 'manifest'}:{location}: {exc.message}") from exc

    repository = _relative_path(str(data["repository"]["path"]), "repository.path")
    repository_path = _contained(REPOSITORY_ROOT, repository)
    generator = _relative_path(str(data["repository"]["generator"]), "repository.generator")
    if not _contained(ROOT, generator).is_file():
        raise BenchmarkError(f"{source or 'manifest'}: missing generator {generator}")
    if not repository_path.is_dir():
        raise BenchmarkError(f"{source or 'manifest'}: missing repository {repository}")
    expected_tree = FixtureTree.from_mapping(
        data["repository"],
        source=f"{source or 'manifest'}:repository",
    )
    verify_fixture_tree(repository_path, expected_tree)
    expected_hashes = {item.path: item.sha256 for item in expected_tree.files}
    actual_meaningful = meaningful_file_count(repository_path, expected_tree)
    if actual_meaningful != data["repository"]["meaningful_files"]:
        raise BenchmarkError(
            f"{source or 'manifest'}: meaningful file count mismatch "
            f"(expected {data['repository']['meaningful_files']}, actual {actual_meaningful})"
        )

    seen_tasks: set[str] = set()
    for task in data["tasks"]:
        task_id = str(task["id"])
        if task_id in seen_tasks:
            raise BenchmarkError(f"{source or 'manifest'}: duplicate task id {task_id!r}")
        seen_tasks.add(task_id)
        prompt = str(task["prompt"]).casefold()
        prompt_terms = set(re.findall(r"[a-z0-9_][a-z0-9_.-]*", prompt))
        if str(data["fixture_id"]).casefold() in prompt_terms:
            raise BenchmarkError(f"{source or 'manifest'}: task {task_id} leaks fixture id")
        expected = task["expected"]
        owners = [
            *expected["primary_owners"],
            *expected["secondary_surfaces"],
            *expected["constraints"],
            *expected["impacts"],
            *(
                owner
                for alternative in task["allowed_alternatives"]
                for owner in alternative
            ),
        ]
        for owner in owners:
            relative = _relative_path(str(owner["path"]), f"tasks.{task_id}.owner.path")
            owner_path = _contained(repository_path, relative)
            if not owner_path.is_file():
                raise BenchmarkError(f"{source or 'manifest'}: missing owner path {relative}")
            expected_file_digest = expected_hashes.get(relative.as_posix())
            if expected_file_digest != owner["sha256"]:
                raise BenchmarkError(
                    f"{source or 'manifest'}: stale evidence for {task_id}:{relative}"
                )
            symbol = str(owner.get("symbol") or "")
            if symbol and symbol not in owner_path.read_text(encoding="utf-8", errors="ignore"):
                raise BenchmarkError(
                    f"{source or 'manifest'}: missing owner symbol {task_id}:{relative}:{symbol}"
                )
            if relative.name.casefold() in prompt_terms or (
                symbol and symbol.casefold() in prompt_terms
            ):
                raise BenchmarkError(f"{source or 'manifest'}: task {task_id} leaks its answer")
        for command in task["verification"]["commands"]:
            if not command or not all(isinstance(part, str) and part for part in command):
                raise BenchmarkError(f"{source or 'manifest'}: invalid command for {task_id}")
            if command[0] != "{python}":
                raise BenchmarkError(
                    f"{source or 'manifest'}: verification command must start with {{python}} "
                    f"for {task_id}"
                )
            for part in command:
                if any(token in part for token in ("\0", "\n", "\r")) or part in {
                    "&&",
                    "||",
                    ";",
                    "|",
                    ">",
                    "<",
                }:
                    raise BenchmarkError(
                        f"{source or 'manifest'}: shell control token in command for {task_id}"
                    )
                if part == "{python}" or part.startswith("-"):
                    continue
                if "/" in part or "\\" in part:
                    relative = _relative_path(part, f"tasks.{task_id}.verification.command")
                    _contained(repository_path, relative)
        for oracle in task["verification"]["oracles"]:
            if oracle["kind"] not in KNOWN_ORACLES:
                raise BenchmarkError(
                    f"{source or 'manifest'}: unsupported oracle {oracle['kind']!r}"
                )
            if oracle.get("path"):
                relative = _relative_path(
                    str(oracle["path"]),
                    f"tasks.{task_id}.verification.oracle.path",
                )
                if not _contained(repository_path, relative).is_file():
                    raise BenchmarkError(
                        f"{source or 'manifest'}: missing oracle evidence path "
                        f"{task_id}:{relative}"
                    )
            evidence_id = str(oracle.get("evidence_id") or "")
            if evidence_id:
                oracle_root = V3_ORACLE_ROOT if int(data.get("fixture_version", 0)) >= 5 else ORACLE_ROOT
                oracle_file = oracle_root / f"{data['fixture_id']}.json"
                if not oracle_file.is_file():
                    raise BenchmarkError(f"{source or 'manifest'}: missing external oracle bundle {oracle_file}")
                bundle = json.loads(oracle_file.read_text(encoding="utf-8"))
                records = bundle.get("tasks", {}) if isinstance(bundle, dict) else {}
                if evidence_id not in records:
                    raise BenchmarkError(f"{source or 'manifest'}: missing external oracle evidence {evidence_id}")
                record = records[evidence_id]
                if not isinstance(record, Mapping):
                    raise BenchmarkError(f"{source or 'manifest'}: malformed external oracle evidence {evidence_id}")
                declared_hash = str(record.get("sha256", ""))
                canonical = {key: value for key, value in record.items() if key != "sha256"}
                actual_hash = hashlib.sha256(
                    json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                if declared_hash != actual_hash:
                    raise BenchmarkError(f"{source or 'manifest'}: stale external oracle evidence {evidence_id}")
                if record.get("task_id") != task_id or record.get("category") != task["category"]:
                    raise BenchmarkError(f"{source or 'manifest'}: external oracle task identity drift for {evidence_id}")
                if record.get("state") != task["state"]["kind"]:
                    raise BenchmarkError(f"{source or 'manifest'}: external oracle state drift for {evidence_id}")
                if not str(record.get("rationale", "")).strip():
                    raise BenchmarkError(f"{source or 'manifest'}: external oracle rationale is empty for {evidence_id}")
                oracle_paths = set(record.get("paths", []))
                expected_paths = {str(owner["path"]) for owner in owners}
                if not expected_paths.issubset(oracle_paths):
                    raise BenchmarkError(f"{source or 'manifest'}: external oracle paths drift for {evidence_id}")
                source_hashes = record.get("source_hashes")
                if not isinstance(source_hashes, Mapping) or source_hashes != {
                    path: expected_hashes[path] for path in sorted(expected_paths)
                }:
                    raise BenchmarkError(f"{source or 'manifest'}: external oracle source hashes drift for {evidence_id}")
        for field in ("protected_paths", "dirty_paths"):
            for value in task["safety"][field]:
                relative = _relative_path(str(value), f"tasks.{task_id}.safety.{field}")
                if not _contained(repository_path, relative).is_file():
                    raise BenchmarkError(
                        f"{source or 'manifest'}: missing safety path {task_id}:{relative}"
                    )
        if "patch" in task:
            relative = _relative_path(str(task["patch"]["path"]), f"tasks.{task_id}.patch.path")
            patch_path = _contained(repository_path, relative)
            if not patch_path.is_file():
                raise BenchmarkError(f"{source or 'manifest'}: missing patch path {task_id}:{relative}")
            content = patch_path.read_text(encoding="utf-8")
            if content.count(task["patch"]["after"]) != 1 or task["patch"]["before"] in content:
                raise BenchmarkError(
                    f"{source or 'manifest'}: frozen patch evidence drift for {task_id}"
                )
            primary_paths = {
                owner["path"]
                for owner in expected["primary_owners"]
            }
            if str(relative) not in primary_paths:
                raise BenchmarkError(
                    f"{source or 'manifest'}: patch path is not a primary owner for {task_id}"
                )
    if data["fixture_id"] in {"schema-migration-service", "plugin-workspace", "component-pipeline"}:
        category_counts = {
            category: sum(task["category"] == category for task in data["tasks"])
            for category in REQUIRED_REALISTIC_CATEGORIES
        }
        expected_counts = {"ownership": 3, "constraint": 4, "impact": 4, "abstention": 3, "decoy": 2, "safety": 2}
        if len(data["tasks"]) != 18 or category_counts != expected_counts:
            raise BenchmarkError(f"{source or 'manifest'}: realistic fixture requires the fixed 18-task category corpus")


def load_manifests(root: Path = MANIFEST_ROOT, *, profile: str | None = None) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise BenchmarkError(f"{path}: manifest must be an object")
        if profile is not None and data.get("ci", {}).get("profile") != profile:
            continue
        validate_manifest(data, source=path)
        fixture_id = str(data["fixture_id"])
        if fixture_id in seen_ids:
            raise BenchmarkError(f"duplicate fixture id {fixture_id!r}")
        seen_ids.add(fixture_id)
        manifests.append(data)
    if not manifests:
        raise BenchmarkError(f"no manifests found under {root}")
    return manifests


@contextmanager
def materialize_repository(manifest: dict[str, Any]) -> Iterator[Path]:
    relative = _relative_path(str(manifest["repository"]["path"]), "repository.path")
    source = _contained(REPOSITORY_ROOT, relative)
    tree = FixtureTree.from_mapping(
        manifest["repository"],
        source=f"{manifest['fixture_id']}:repository",
    )
    verify_fixture_tree(source, tree)
    with tempfile.TemporaryDirectory(prefix=f"benchmark-{manifest['fixture_id']}-") as temporary:
        destination = Path(temporary) / "repo"
        destination.mkdir()
        for item in tree.files:
            source_path = _contained(source, PurePosixPath(item.path))
            destination_path = _contained(destination, PurePosixPath(item.path))
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        yield destination
