from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType


def scaffold_module(root: Path) -> ModuleType:
    path = root / "skills" / "engineering" / "plan-change" / "scripts" / "plan_contract.py"
    spec = importlib.util.spec_from_file_location("hardening_scaffold_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hydrated_scaffold(root: Path, repo: Path, tier: str, domains: list[str]) -> str:
    module = scaffold_module(root)
    (repo / "src").mkdir(exist_ok=True)
    source = "def target(raw: str) -> str:\n    return raw.strip()\n"
    (repo / "src" / "target.py").write_text(source, encoding="utf-8")
    excerpt = "def target(raw: str) -> str:\n"
    text = module.render_scaffold(tier, "bug-fix", domains)
    replacements = {
        "REPLACE_CURRENT_PATH": "src/target.py",
        "REPLACE_CURRENT_RANGE": "1-1",
        "REPLACE_CURRENT_ANCHOR": "target",
        "REPLACE_CURRENT_HASH": hashlib.sha256(excerpt.encode()).hexdigest(),
        "REPLACE_CURRENT_FILE_HASH": hashlib.sha256((repo / "src" / "target.py").read_bytes()).hexdigest(),
        "REPLACE_EXACT_SIGNATURE": "raw: str",
        "REPLACE_EXACT_RETURN": "str",
        "REPLACE_TARGETED_TEST.py": "test_target.py",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    for domain in domains:
        text = text.replace(f"REPLACE_{domain}.py", f"test_{domain}.py")
    return text
