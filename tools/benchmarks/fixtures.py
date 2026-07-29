from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "benchmarks"
SCHEMA_PATH = BENCHMARK_ROOT / "schema" / "fixture-manifest.schema.json"
MANIFEST_ROOT = BENCHMARK_ROOT / "manifests"
REPOSITORY_ROOT = BENCHMARK_ROOT / "repos"
KNOWN_ORACLES = {"python-test", "path-set", "ownership", "abstention"}


class BenchmarkError(ValueError):
    """Raised when benchmark data violates a safety or integrity contract."""


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


def repository_digest(root: Path) -> str:
    """Hash relative paths and bytes for a stable, machine-independent tree digest."""
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        relative_text = relative.as_posix()
        digest.update(relative_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meaningful_file_count(root: Path) -> int:
    return sum(
        1
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name not in {"__init__.py", ".gitattributes"}
        and "generated" not in path.relative_to(root).parts
        and not path.name.startswith(("component_", "check_component_", "service-"))
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
    for candidate in repository_path.rglob("*"):
        if not candidate.is_symlink():
            continue
        try:
            candidate.resolve().relative_to(repository_path.resolve())
        except ValueError as exc:
            raise BenchmarkError(
                f"{source or 'manifest'}: symlink escapes repository: "
                f"{candidate.relative_to(repository_path).as_posix()}"
            ) from exc
    actual_digest = repository_digest(repository_path)
    expected_digest = str(data["repository"]["sha256"])
    if actual_digest != expected_digest:
        raise BenchmarkError(
            f"{source or 'manifest'}: repository digest mismatch "
            f"(expected {expected_digest}, actual {actual_digest})"
        )
    actual_meaningful = meaningful_file_count(repository_path)
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
            actual_file_digest = file_digest(owner_path)
            if actual_file_digest != owner["sha256"]:
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


def load_manifests(root: Path = MANIFEST_ROOT) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise BenchmarkError(f"{path}: manifest must be an object")
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
    with tempfile.TemporaryDirectory(prefix=f"benchmark-{manifest['fixture_id']}-") as temporary:
        destination = Path(temporary) / "repo"
        shutil.copytree(source, destination, symlinks=True)
        yield destination
