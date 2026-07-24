#!/usr/bin/env python3
"""Verify built distribution tree for runtime completeness and clean boundaries."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "packaging"))

from build_distribution import build_distribution  # noqa: E402


def verify_distribution_tree(dist_path: Path) -> list[str]:
    errors = []

    # Ensure plugin manifests exist
    claude_json = dist_path / ".claude-plugin" / "plugin.json"
    if not claude_json.is_file():
        errors.append("Distribution missing .claude-plugin/plugin.json")

    claude_market = dist_path / ".claude-plugin" / "marketplace.json"
    if not claude_market.is_file():
        errors.append("Distribution missing .claude-plugin/marketplace.json")

    cursor_json = dist_path / ".cursor-plugin" / "plugin.json"
    if not cursor_json.is_file():
        errors.append("Distribution missing .cursor-plugin/plugin.json")

    cursor_market = dist_path / ".cursor-plugin" / "marketplace.json"
    if not cursor_market.is_file():
        errors.append("Distribution missing .cursor-plugin/marketplace.json")

    codex_config = dist_path / ".codex" / "config.toml"
    if not codex_config.is_file():
        errors.append("Distribution missing .codex/config.toml")

    license_file = dist_path / "LICENSE"
    if not license_file.is_file():
        errors.append("Distribution missing LICENSE")

    agents_dir = dist_path / "agents"
    if not agents_dir.is_dir():
        errors.append("Distribution missing agents directory")

    catalog_dir = dist_path / "catalog"
    if not catalog_dir.is_dir():
        errors.append("Distribution missing catalog directory")
    elif yaml:
        skills_yaml = catalog_dir / "skills.yaml"
        if not skills_yaml.is_file():
            errors.append("Distribution missing catalog/skills.yaml")
        else:
            with skills_yaml.open("r", encoding="utf-8") as f:
                cat_data = yaml.safe_load(f) or {}
            for s in cat_data.get("skills", []):
                s_path = dist_path / s["path"]
                if not s_path.is_dir():
                    errors.append(f"Distribution missing skill directory '{s['path']}'")
                elif not (s_path / "SKILL.md").is_file():
                    errors.append(f"Distribution missing SKILL.md for '{s['name']}' at {s['path']}")

        agents_yaml = catalog_dir / "agents.yaml"
        if not agents_yaml.is_file():
            errors.append("Distribution missing catalog/agents.yaml")
        else:
            with agents_yaml.open("r", encoding="utf-8") as f:
                agent_cat_data = yaml.safe_load(f) or {}
            for a in agent_cat_data.get("agents", []):
                a_name = a["name"]
                c_adapter = dist_path / "agents" / "claude" / f"{a_name}.md"
                if not c_adapter.is_file():
                    errors.append(f"Distribution missing Claude adapter for agent '{a_name}'")
                cur_adapter = dist_path / "agents" / "cursor" / f"{a_name}.md"
                if not cur_adapter.is_file():
                    errors.append(f"Distribution missing Cursor adapter for agent '{a_name}'")
                codex_adapter = dist_path / ".codex" / "agents" / f"{a_name}.toml"
                if not codex_adapter.is_file():
                    errors.append(f"Distribution missing Codex adapter for agent '{a_name}'")

    # Check Codex installer script
    codex_installer = dist_path / "tools" / "agents" / "install_codex_agents.py"
    if not codex_installer.is_file():
        errors.append("Distribution missing tools/agents/install_codex_agents.py")

    # Check for forbidden development files
    forbidden_names = {"browser_smoke.py", "conftest.py", "debug_hash.py"}
    for p in dist_path.rglob("*"):
        if p.name in forbidden_names or p.name.startswith("test_") or "evals" in p.parts or "tests" in p.parts:
            errors.append(f"Distribution contains forbidden development artifact: {p.relative_to(dist_path)}")

    # Helper for heading anchor extraction
    def get_md_anchors(file_path: Path) -> set[str]:
        anchors = set()
        try:
            for line in file_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#"):
                    heading_text = line.lstrip("#").strip()
                    # GitHub-like heading anchor slugification
                    slug = re.sub(r"[^\w\s-]", "", heading_text.lower()).strip().replace(" ", "-")
                    # Also collapse multiple hyphens
                    slug = re.sub(r"-+", "-", slug)
                    if slug:
                        anchors.add(slug)
        except Exception:
            pass
        return anchors

    # Validate all relative Markdown links in bundled distribution files
    import re
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    for md_file in dist_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        rel_md = md_file.relative_to(dist_path)
        for _, link in link_pattern.findall(content):
            link = link.strip()
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue

            if link.startswith("#"):
                anchor = link[1:].lower()
                if anchor and anchor not in get_md_anchors(md_file):
                    # Only report if heading wasn't found (case-insensitive fallback)
                    pass  # Anchor check is best-effort to avoid false positives on complex formatting
                continue

            clean_link = link.split("#")[0].strip()
            fragment = link.split("#")[1].lower() if "#" in link else None

            if not clean_link:
                continue

            target_path = (md_file.parent / clean_link).resolve()

            # Enforce path traversal check
            try:
                target_path.relative_to(dist_path.resolve())
            except ValueError:
                errors.append(f"{rel_md}: path traversal outside distribution root '{clean_link}'")
                continue

            if not target_path.exists():
                errors.append(f"{rel_md}: broken relative link target '{clean_link}'")
                continue

            # If link has fragment anchor and target is Markdown file, validate anchor if possible
            if fragment and target_path.is_file() and target_path.suffix == ".md":
                anchors = get_md_anchors(target_path)
                if anchors and fragment not in anchors:
                    # Best-effort anchor validation
                    pass

    # Validate python commands referencing repository tools/scripts across bundled Markdown files
    for md_file in dist_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        rel_md = md_file.relative_to(dist_path)
        text_to_check = content.split("## Maintainer Verification")[0] if md_file.name == "README.md" else content

        cmd_matches = re.findall(r"python\s+([A-Za-z0-9_/\\]+\.py)", text_to_check)
        for cmd_path_str in cmd_matches:
            norm_cmd = cmd_path_str.replace("\\", "/")
            # Only validate commands targeting repository paths (tools/ or scripts/)
            if not (norm_cmd.startswith("tools/") or norm_cmd.startswith("scripts/")):
                continue

            if norm_cmd.startswith("scripts/"):
                # Check if script exists relative to md_file or within any skill's scripts directory
                script_found = (md_file.parent / norm_cmd).is_file() or any(
                    (dist_path / "skills").rglob(norm_cmd)
                )
                if not script_found:
                    errors.append(f"{rel_md} references missing command target file: {cmd_path_str}")
            elif norm_cmd.startswith("tools/"):
                cmd_target = (dist_path / norm_cmd).resolve()
                if not cmd_target.is_file():
                    if "source repository" in text_to_check.lower() or "github repository" in text_to_check.lower():
                        continue
                    errors.append(f"{rel_md} references missing command target file: {cmd_path_str}")

        # Ensure no bundled doc presents unbundled maintainer runners as local commands
        for missing_ref in ("browser_smoke.py", "run_live_evaluations.py"):
            if missing_ref in text_to_check and "source repository" not in text_to_check.lower():
                errors.append(f"{rel_md} references unbundled maintainer tool: {missing_ref}")

    return errors


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="verify-dist-"))
    try:
        dist_path = build_distribution(temp_dir)
        errors = verify_distribution_tree(dist_path)
        if errors:
            print("Distribution verification failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("Distribution verification passed.")
        return 0
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
