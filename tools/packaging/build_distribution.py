#!/usr/bin/env python3
"""Build clean temporary distribution tree for verification."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"


def build_distribution(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    # Copy canonical skill runtime trees
    for skill in catalog.get("skills", []):
        src_path = ROOT / skill["path"]
        dest_path = output_dir / skill["path"]
        dest_path.mkdir(parents=True, exist_ok=True)

        for p in src_path.rglob("*"):
            rel = p.relative_to(src_path)
            # Exclude tests/evals/fixtures if any exist
            if any(part in ("tests", "evals", "fixtures") for part in rel.parts):
                continue
            dest = dest_path / rel
            if p.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            elif p.is_file():
                shutil.copy2(p, dest)

    # Copy distribution manifests & adapters
    claude_src = ROOT / ".claude-plugin"
    if claude_src.is_dir():
        shutil.copytree(claude_src, output_dir / ".claude-plugin")

    cursor_src = ROOT / ".cursor-plugin"
    if cursor_src.is_dir():
        shutil.copytree(cursor_src, output_dir / ".cursor-plugin")

    codex_src = ROOT / ".codex"
    if codex_src.is_dir():
        shutil.copytree(codex_src, output_dir / ".codex")

    catalog_src = ROOT / "catalog"
    if catalog_src.is_dir():
        shutil.copytree(catalog_src, output_dir / "catalog")

    agents_src = ROOT / "agents"
    if agents_src.is_dir():
        shutil.copytree(agents_src, output_dir / "agents")

    # Copy user-facing documentation
    docs_src = ROOT / "docs"
    if docs_src.is_dir():
        dest_docs = output_dir / "docs"
        dest_docs.mkdir(parents=True, exist_ok=True)
        allowed_root_docs = {"getting-started.md", "installation.md", "compatibility.md", "agents.md", "workflow.md", "safety.md"}
        allowed_subdirs = {"skills", "agents"}
        for p in docs_src.rglob("*"):
            rel = p.relative_to(docs_src)
            first_part = rel.parts[0]
            if len(rel.parts) == 1:
                if first_part not in allowed_root_docs:
                    continue
            elif len(rel.parts) > 1:
                if first_part not in allowed_subdirs:
                    continue
            dest = dest_docs / rel
            if p.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            elif p.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)

    # Copy Codex installer script
    installer_src = ROOT / "tools" / "agents" / "install_codex_agents.py"
    if installer_src.is_file():
        dest_tools_agents = output_dir / "tools" / "agents"
        dest_tools_agents.mkdir(parents=True, exist_ok=True)
        shutil.copy2(installer_src, dest_tools_agents / "install_codex_agents.py")

    # Copy root documentation and metadata files
    for root_file in ("README.md", "VERSION", "LICENSE", "SECURITY.md", "CHANGELOG.md", "pyproject.toml"):
        src_f = ROOT / root_file
        if src_f.is_file():
            shutil.copy2(src_f, output_dir / root_file)

    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build clean skill distribution tree.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    if args.output_dir is None:
        target = Path(tempfile.mkdtemp(prefix="skills-dist-"))
        cleanup = True
    else:
        target = args.output_dir
        cleanup = False

    try:
        built_path = build_distribution(target)
        print(f"Distribution successfully built at: {built_path}")
    finally:
        if cleanup and target.exists():
            shutil.rmtree(target, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
