from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "packaging"))

import build_distribution  # noqa: E402
import verify_distribution  # noqa: E402


def test_build_and_verify_clean_distribution() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="test-dist-"))
    try:
        dist_path = build_distribution.build_distribution(temp_dir)
        errors = verify_distribution.verify_distribution_tree(dist_path)
        assert not errors, "Distribution verification failed:\n" + "\n".join(errors)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
