from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import _hash  # noqa: E402

SCRIPT = SCRIPTS / "hash_excerpt.py"
FIXTURE = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / "tiny" / "src" / "names.py"


def test_hash_excerpt_matches_runtime_fingerprints() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--path",
            str(FIXTURE),
            "--start-line",
            "1",
            "--end-line",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    source = FIXTURE.read_text(encoding="utf-8", errors="replace").splitlines()
    excerpt = "\n".join(source[0:2]) + "\n"
    assert result.stdout.splitlines() == [
        f"excerpt-sha256: {_hash(excerpt.encode())}",
        f"file-sha256: {_hash(FIXTURE.read_bytes())}",
    ]


def test_hash_excerpt_rejects_out_of_bounds_range() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--path",
            str(FIXTURE),
            "--start-line",
            "1",
            "--end-line",
            "3",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "inclusive range within 1-2" in result.stderr
