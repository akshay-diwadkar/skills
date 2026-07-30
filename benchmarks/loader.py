from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

FIXTURE_ROOT = Path(__file__).with_name("fixtures")
REPOSITORY_ROOT = Path(__file__).with_name("repos")
SPLIT_FILES = {
    "tuning": FIXTURE_ROOT / "adversarial_cases.json",
    "heldout": FIXTURE_ROOT / "heldout_cases.json",
}
Split = Literal["tuning", "heldout"]


class FixtureLeakageError(ValueError):
    """Raised when tuning and held-out cases are not independent."""


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    split: Split
    repository: str
    query: str
    expected_owner_sets: tuple[tuple[str, ...], ...]
    expected_constraints: tuple[str, ...]
    expected_impacts: tuple[str, ...]
    expected_status: str
    tags: tuple[str, ...]


def _case_signature(case: BenchmarkCase) -> str:
    normalized = " ".join(case.query.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _safe_path(value: object, *, field: str) -> PurePosixPath:
    path = PurePosixPath(str(value))
    if path.is_absolute() or ".." in path.parts or "\\" in str(value):
        raise ValueError(f"{field} must be a repository-relative POSIX path")
    return path


def _load_file(path: Path, expected_split: Split) -> list[BenchmarkCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("split") != expected_split:
        raise ValueError(f"{path}: invalid schema version or split")
    cases: list[BenchmarkCase] = []
    seen: set[str] = set()
    for raw in payload.get("cases", []):
        case_id = str(raw["id"])
        if case_id in seen:
            raise ValueError(f"{path}: duplicate case id {case_id!r}")
        seen.add(case_id)
        repository = str(raw["repository"])
        repository_root = REPOSITORY_ROOT / repository
        if not repository_root.is_dir():
            raise ValueError(f"{path}: unknown repository {repository!r}")
        expected = raw["expected"]
        owner_sets = tuple(
            tuple(str(_safe_path(item, field=f"{case_id}.owners")) for item in owner_set)
            for owner_set in expected.get("owner_sets", [])
        )
        if expected["status"] != "abstain" and not owner_sets:
            raise ValueError(f"{path}: non-abstaining case {case_id!r} needs an owner set")
        evidence = raw.get("evidence", [])
        evidence_paths: set[str] = set()
        for item in evidence:
            relative = _safe_path(item["path"], field=f"{case_id}.evidence")
            target = repository_root.joinpath(*relative.parts)
            if not target.is_file():
                raise ValueError(f"{path}: missing evidence {repository}:{relative}")
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != item["sha256"]:
                raise ValueError(f"{path}: stale evidence hash {repository}:{relative}")
            evidence_paths.add(relative.as_posix())
        constraints = tuple(
            str(_safe_path(item, field=f"{case_id}.constraints"))
            for item in expected.get("constraints", [])
        )
        impacts = tuple(
            str(_safe_path(item, field=f"{case_id}.impacts"))
            for item in expected.get("impacts", [])
        )
        expected_paths = {
            value
            for owner_set in owner_sets
            for value in owner_set
        } | set(constraints) | set(impacts)
        if not expected_paths <= evidence_paths:
            missing = sorted(expected_paths - evidence_paths)
            raise ValueError(f"{path}: expected paths lack hash-bound evidence: {missing}")
        cases.append(
            BenchmarkCase(
                id=case_id,
                split=expected_split,
                repository=repository,
                query=str(raw["query"]),
                expected_owner_sets=owner_sets,
                expected_constraints=constraints,
                expected_impacts=impacts,
                expected_status=str(expected["status"]),
                tags=tuple(str(tag) for tag in raw.get("tags", [])),
            )
        )
    if not cases:
        raise ValueError(f"{path}: fixture split must not be empty")
    return cases


def assert_split_independence(
    tuning: list[BenchmarkCase], heldout: list[BenchmarkCase]
) -> None:
    tuning_ids = {case.id for case in tuning}
    heldout_ids = {case.id for case in heldout}
    duplicate_ids = tuning_ids & heldout_ids
    tuning_signatures = {_case_signature(case) for case in tuning}
    heldout_signatures = {_case_signature(case) for case in heldout}
    duplicate_queries = tuning_signatures & heldout_signatures
    if duplicate_ids or duplicate_queries:
        raise FixtureLeakageError(
            "benchmark splits overlap: "
            f"ids={sorted(duplicate_ids)}, query_hashes={sorted(duplicate_queries)}"
        )


def load_case_splits() -> dict[Split, list[BenchmarkCase]]:
    tuning = _load_file(SPLIT_FILES["tuning"], "tuning")
    heldout = _load_file(SPLIT_FILES["heldout"], "heldout")
    assert_split_independence(tuning, heldout)
    return {"tuning": tuning, "heldout": heldout}


def load_cases(split: Split) -> list[BenchmarkCase]:
    """Load exactly one split so tuning code cannot accidentally receive held-out cases."""
    if split not in SPLIT_FILES:
        raise ValueError(f"unknown benchmark split: {split!r}")
    splits = load_case_splits()
    return list(splits[split])
