from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "engineering" / "map-codebase"
SCRIPTS_DIR = SKILL_DIR / "scripts"
REQUIREMENTS = SKILL_DIR / "requirements.txt"


def _normalise_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def test_every_direct_third_party_import_is_declared() -> None:
    imported_roots: set[str] = set()
    for path in SCRIPTS_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

    local_roots = {path.stem for path in SCRIPTS_DIR.glob("*.py")}
    local_roots.update(path.name for path in SCRIPTS_DIR.iterdir() if path.is_dir())
    third_party = imported_roots - set(sys.stdlib_module_names) - local_roots

    declared = {
        _normalise_distribution(match.group(1))
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^\s*([A-Za-z0-9_.-]+)", line))
    }
    missing = {
        module
        for module in third_party
        if _normalise_distribution(module) not in declared
    }

    assert missing == set()
