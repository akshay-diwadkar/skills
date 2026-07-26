import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import _literal_split, resolve_task

CASES = [
    ("Repair retry behavior", "backoff", "BackoffOwner"),
    ("Strengthen login credentials", "authentication", "AuthenticationOwner"),
    ("Load settings safely", "options", "OptionsOwner"),
    ("Handle runtime failures", "exception", "ExceptionOwner"),
    ("Speed up the cache layer", "memoization", "MemoizationOwner"),
    ("Find matching items", "search", "SearchOwner"),
    ("Restrict account access", "authorization", "AuthorizationOwner"),
    ("Apply request ratelimits", "throttle", "ThrottleOwner"),
    ("Delete archived entries", "removal", "RemovalOwner"),
    ("Serialize the payload", "encoding", "EncodingOwner"),
    ("Parse the response body", "decoding", "DecodingOwner"),
    ("Enforce the timeout", "deadline", "DeadlineOwner"),
    ("Drain the queue", "worker", "WorkerOwner"),
    ("Verify incoming values", "validation", "ValidationOwner"),
    ("Insert a new record", "creation", "CreationOwner"),
    ("Modify the published contract", "revision", "RevisionOwner"),
]


@pytest.mark.parametrize(("task", "stem", "symbol"), CASES)
def test_non_literal_task_resolves_with_synonym_evidence(
    tmp_path: Path, task: str, stem: str, symbol: str
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for _, candidate_stem, candidate_symbol in CASES:
        (src / f"{candidate_stem}.py").write_text(
            f"class {candidate_symbol}:\n    pass\n",
            encoding="utf-8",
        )
    output = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, output)

    expected_path = f"src/{stem}.py"
    assert not (_literal_split(task) & _literal_split(f"{expected_path} {symbol}"))

    result = resolve_task(tmp_path, task, output, phase=1)

    assert result["targets"][0]["path"] == expected_path
    assert result["targets"][0]["symbol"] == symbol
    assert any(item.startswith("synonym_token: ") for item in result["targets"][0]["evidence"])
