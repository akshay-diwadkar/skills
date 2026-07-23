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

    # Copy distribution manifests
    plugin_src = ROOT / ".claude-plugin"
    if plugin_src.is_dir():
        shutil.copytree(plugin_src, output_dir / ".claude-plugin")

    shutil.copy2(ROOT / "README.md", output_dir / "README.md")
    shutil.copy2(ROOT / "VERSION", output_dir / "VERSION")

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
