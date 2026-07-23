#!/usr/bin/env python3
"""Installer script for Codex project custom agents."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("Error: tomllib (Python 3.11+) or tomli is required.", file=sys.stderr)
        sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_CODEX_DIR = ROOT / ".codex"


def merge_config_toml(existing_text: str, new_text: str) -> str:
    """Merge [agents] section into existing config.toml while preserving unrelated text."""
    if "[agents]" in existing_text:
        # If [agents] already exists, return existing text unchanged to preserve target config
        return existing_text
    return existing_text.rstrip() + "\n\n" + new_text.strip() + "\n"


def install_codex_agents(target_dir: Path, write: bool = False, force: bool = False) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    errors: list[str] = []

    target_dir = target_dir.resolve()
    target_codex = target_dir / ".codex"
    target_agents_dir = target_codex / "agents"

    source_agents_dir = SOURCE_CODEX_DIR / "agents"
    if not source_agents_dir.is_dir():
        return [], ["Source .codex/agents directory not found"]

    source_agent_files = list(source_agents_dir.glob("*.toml"))
    if not source_agent_files:
        return [], ["No agent TOML files found in source"]

    # 1. Inspect agent TOML files
    for src_file in source_agent_files:
        dest_file = target_agents_dir / src_file.name

        # Parse source to verify valid TOML
        try:
            with src_file.open("rb") as f:
                tomllib.load(f)
        except Exception as exc:
            errors.append(f"Invalid source TOML {src_file.name}: {exc}")
            continue

        if dest_file.is_file():
            # Check if contents match
            src_bytes = src_file.read_bytes()
            dest_bytes = dest_file.read_bytes()
            if src_bytes == dest_bytes:
                actions.append(f"SKIP (identical): {dest_file.relative_to(target_dir)}")
            elif not force:
                errors.append(f"Destination {dest_file.relative_to(target_dir)} exists and differs. Use --force to overwrite.")
            else:
                actions.append(f"REPLACE: {dest_file.relative_to(target_dir)}")
                if write:
                    dest_file.write_bytes(src_bytes)
        else:
            actions.append(f"CREATE: {dest_file.relative_to(target_dir)}")
            if write:
                target_agents_dir.mkdir(parents=True, exist_ok=True)
                dest_file.write_bytes(src_file.read_bytes())

    # 2. Inspect config.toml
    source_config_file = SOURCE_CODEX_DIR / "config.toml"
    if source_config_file.is_file():
        dest_config_file = target_codex / "config.toml"
        source_config_text = source_config_file.read_text(encoding="utf-8")

        if dest_config_file.is_file():
            existing_config_text = dest_config_file.read_text(encoding="utf-8")
            merged = merge_config_toml(existing_config_text, source_config_text)
            if merged != existing_config_text:
                actions.append(f"MERGE: {dest_config_file.relative_to(target_dir)}")
                if write:
                    dest_config_file.write_text(merged, encoding="utf-8")
            else:
                actions.append(f"SKIP (config intact): {dest_config_file.relative_to(target_dir)}")
        else:
            actions.append(f"CREATE: {dest_config_file.relative_to(target_dir)}")
            if write:
                target_codex.mkdir(parents=True, exist_ok=True)
                dest_config_file.write_text(source_config_text, encoding="utf-8")

    return actions, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Codex project custom agents into a target project.")
    parser.add_argument("--target", type=Path, required=True, help="Target project root directory")
    parser.add_argument("--write", action="store_true", help="Perform changes (default is dry-run)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing differing files")
    args = parser.parse_args()

    actions, errors = install_codex_agents(args.target, write=args.write, force=args.force)

    mode_str = "WRITE MODE" if args.write else "DRY-RUN MODE (no files modified)"
    print(f"Codex Agent Installer [{mode_str}]")
    print(f"Target: {args.target.resolve()}")
    print("-" * 50)

    for action in actions:
        print(f"  - {action}")

    if errors:
        print("\nErrors / Conflicts:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not args.write:
        print("\nTo apply these changes, re-run with --write")

    return 0


if __name__ == "__main__":
    sys.exit(main())
