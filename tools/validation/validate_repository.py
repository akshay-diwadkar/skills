#!/usr/bin/env python3
"""Validate the standalone skill repository."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "skills"
VERSION_PATH = ROOT / "VERSION"
README_PATH = ROOT / "README.md"
VERSION_DESCRIPTION_PATH = ROOT / "VERSION_DESC.md"
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
ROUTER_SCHEMA_PATH = (
    ROOT / "skills" / "engineering" / "route-engineering-work" / "schemas" / "routing-decision.schema.json"
)
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
LATEST_RELEASE_BADGE_RE = re.compile(
    r"\[!\[Latest Release\]\((?P<badge_url>[^)]+)\)\]\((?P<target_url>[^)]+)\)"
)
LATEST_RELEASE_URL = "https://github.com/akshay-diwadkar/skills/releases/latest"
EXPECTED_MARKETPLACE_GROUPS = {
    "engineering-skills": {
        "./skills/engineering/audit-codebase",
        "./skills/engineering/design-codebase",
        "./skills/engineering/diagram-codebase",
        "./skills/engineering/implement-plan",
        "./skills/engineering/map-codebase",
        "./skills/engineering/optimize-codebase",
        "./skills/engineering/plan-change",
        "./skills/engineering/route-engineering-work",
        "./skills/engineering/scope-issue",
    },
    "technical-communication-skills": {
        "./skills/technical-communication/manualize",
    },
}
ROUTED_SKILLS = {
    "map-codebase",
    "design-codebase",
    "plan-change",
    "implement-plan",
    "audit-codebase",
    "optimize-codebase",
    "scope-issue",
    "diagram-codebase",
    "manualize",
}
ROUTER_FIELDS = {
    "primary_skill",
    "prerequisites",
    "follow_up",
    "reason",
    "confidence",
    "next_action",
    "allowed_actions",
    "forbidden_actions",
}
ROUTER_ALLOWED_ACTIONS = [
    "read_request",
    "read_repository_facts",
    "emit_routing_decision",
]
ROUTER_FORBIDDEN_ACTIONS = [
    "plan",
    "edit_source",
    "publish_issues",
    "commit",
    "push",
    "create_pull_request",
    "execute_selected_workflow",
]
ALLOWED_TOP_LEVEL = {
    "SKILL.md",
    "scripts",
    "references",
    "schemas",
    "templates",
    "assets",
    "requirements.txt",
    ".env.example",
    "README.md",
    "CHANGELOG.md",
}
FORBIDDEN_PARTS = {"agents", "evals", "fixtures", "__pycache__"}
ALLOWED_DOMAIN_FILES = {"README.md"}
RETIRED_PATHS = (
    "catalog",
    "docs",
    "skills-lock.json",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "tools/catalog",
    "tools/packaging",
    "tools/release",
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/scripts",
    ".github/workflows/release.yml",
    ".github/workflows/repository-contract.yml",
)


def tracked_files() -> list[Path]:
    """Return repository files tracked by Git, excluding missing paths."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return []
    return [
        path
        for relative in result.stdout.decode("utf-8").split("\0")
        if relative
        for path in [ROOT / relative]
        if path.is_file()
    ]


def discover_skills() -> list[Path]:
    if not SKILLS_ROOT.is_dir():
        return []
    return sorted(
        skill
        for domain in SKILLS_ROOT.iterdir()
        if domain.is_dir()
        for skill in domain.iterdir()
        if skill.is_dir()
    )


def validate_domain_layout() -> list[str]:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir():
        return errors
    for child in SKILLS_ROOT.iterdir():
        if not child.is_dir():
            errors.append(f"{child.relative_to(ROOT)}: skill root may contain only domain directories")
            continue
        for item in child.iterdir():
            if not item.is_dir() and item.name not in ALLOWED_DOMAIN_FILES:
                errors.append(f"{item.relative_to(ROOT)}: domain may contain only skill directories")
    return errors


def validate_frontmatter(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.relative_to(ROOT)}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{skill_md.relative_to(ROOT)}: missing YAML frontmatter"]
    frontmatter = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    version = re.search(r"^version:\s*(.+)$", frontmatter, re.MULTILINE)
    errors: list[str] = []
    if not name or name.group(1).strip() != skill_dir.name:
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter name must match the skill directory")
    if not description or not description.group(1).strip():
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter description is required")
    if not version:
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter version is required")
    elif not SEMVER_RE.fullmatch(version.group(1).strip()):
        errors.append(
            f"{skill_md.relative_to(ROOT)}: version "
            f"{version.group(1).strip()!r} is not valid Semantic Versioning"
        )
    return errors


def validate_version() -> list[str]:
    if not VERSION_PATH.is_file():
        return ["Missing VERSION"]
    version = VERSION_PATH.read_text(encoding="utf-8").strip()
    if not SEMVER_RE.fullmatch(version):
        return [f"VERSION {version!r} is not valid Semantic Versioning"]
    return []


def validate_version_description(path: Path | None = None) -> list[str]:
    """Require usable release notes for the package version."""
    path = path or VERSION_DESCRIPTION_PATH
    if not path.is_file():
        return ["Missing VERSION_DESC.md"]
    if not path.read_text(encoding="utf-8").strip():
        return ["VERSION_DESC.md must contain the GitHub release summary"]
    return []


def validate_readme_release_link(
    readme_path: Path | None = None,
    version_path: Path | None = None,
) -> list[str]:
    """Keep the dynamic latest-release badge cache key aligned with VERSION."""
    readme_path = readme_path or README_PATH
    version_path = version_path or VERSION_PATH
    if not readme_path.is_file():
        return ["Missing README.md"]
    if not version_path.is_file():
        return ["README.md: cannot validate latest-release badge without VERSION"]

    match = LATEST_RELEASE_BADGE_RE.search(readme_path.read_text(encoding="utf-8"))
    if match is None:
        return ["README.md: missing Latest Release badge"]

    errors: list[str] = []
    if match.group("target_url") != LATEST_RELEASE_URL:
        errors.append(f"README.md: Latest Release badge must target {LATEST_RELEASE_URL}")

    version = version_path.read_text(encoding="utf-8").strip()
    cache_versions = parse_qs(urlsplit(match.group("badge_url")).query).get("v", [])
    if cache_versions != [version]:
        errors.append(
            "README.md: Latest Release badge cache key must match VERSION "
            f"(expected v={version})"
        )
    return errors


def validate_marketplace() -> list[str]:
    if not MARKETPLACE_PATH.is_file():
        return ["Missing .claude-plugin/marketplace.json"]

    try:
        payload = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f".claude-plugin/marketplace.json: invalid JSON: {exc}"]

    plugins = payload.get("plugins") if isinstance(payload, dict) else None
    if not isinstance(plugins, list):
        return [".claude-plugin/marketplace.json: plugins must be an array"]

    errors: list[str] = []
    actual_groups: dict[str, set[str]] = {}
    all_paths: list[str] = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            errors.append(".claude-plugin/marketplace.json: each plugin must be an object")
            continue
        name = plugin.get("name")
        source = plugin.get("source")
        skills = plugin.get("skills")
        if not isinstance(name, str) or not name:
            errors.append(".claude-plugin/marketplace.json: each plugin requires a name")
            continue
        if source != "./":
            errors.append(f".claude-plugin/marketplace.json: {name} source must be './'")
        if not isinstance(skills, list) or not all(isinstance(path, str) for path in skills):
            errors.append(f".claude-plugin/marketplace.json: {name} skills must be an array of paths")
            continue
        if name in actual_groups:
            errors.append(f".claude-plugin/marketplace.json: duplicate plugin group {name}")
            continue
        path_set = set(skills)
        if len(path_set) != len(skills):
            errors.append(f".claude-plugin/marketplace.json: {name} contains duplicate skill paths")
        actual_groups[name] = path_set
        all_paths.extend(skills)
        for skill_path in skills:
            if not skill_path.startswith("./skills/"):
                errors.append(f".claude-plugin/marketplace.json: invalid skill path {skill_path!r}")
                continue
            resolved = ROOT / skill_path.removeprefix("./")
            if not (resolved / "SKILL.md").is_file():
                errors.append(f".claude-plugin/marketplace.json: missing {skill_path}/SKILL.md")

    if set(actual_groups) != set(EXPECTED_MARKETPLACE_GROUPS):
        errors.append(
            ".claude-plugin/marketplace.json: plugin groups must be exactly "
            f"{sorted(EXPECTED_MARKETPLACE_GROUPS)}"
        )
    for name, expected_paths in EXPECTED_MARKETPLACE_GROUPS.items():
        if name in actual_groups and actual_groups[name] != expected_paths:
            errors.append(
                f".claude-plugin/marketplace.json: {name} must contain exactly "
                f"{sorted(expected_paths)}"
            )
    if len(all_paths) != len(set(all_paths)):
        errors.append(".claude-plugin/marketplace.json: skill paths must belong to only one group")
    if (ROOT / ".claude-plugin" / "plugin.json").exists():
        errors.append(".claude-plugin/plugin.json must remain absent to preserve two installer groups")
    for manifest_name in ("skill.yaml", "skill.yml", "skill.json"):
        if (ROOT / manifest_name).exists():
            errors.append(f"{manifest_name} is unsupported and must remain absent")
    return errors


def validate_router_contract(path: Path | None = None) -> list[str]:
    """Keep the suite router's machine and safety contract exact."""
    path = path or ROUTER_SCHEMA_PATH
    if not path.is_file():
        return [f"Missing {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{path.relative_to(ROOT)}: invalid JSON: {exc}"]

    errors: list[str] = []
    properties = payload.get("properties")
    required = payload.get("required")
    definitions = payload.get("$defs")
    if not isinstance(properties, dict) or set(properties) != ROUTER_FIELDS:
        errors.append("route-engineering-work: decision properties must remain exact")
        return errors
    if not isinstance(required, list) or set(required) != ROUTER_FIELDS:
        errors.append("route-engineering-work: every decision property must remain required")
    if not isinstance(definitions, dict):
        errors.append("route-engineering-work: decision schema must define routed skills")
    else:
        skill = definitions.get("skill")
        skill_enum = skill.get("enum") if isinstance(skill, dict) else None
        if not isinstance(skill_enum, list) or set(skill_enum) != ROUTED_SKILLS:
            errors.append("route-engineering-work: routed skill enum must remain exact")
    if properties["allowed_actions"].get("const") != ROUTER_ALLOWED_ACTIONS:
        errors.append("route-engineering-work: allowed actions must remain read-only")
    if properties["forbidden_actions"].get("const") != ROUTER_FORBIDDEN_ACTIONS:
        errors.append("route-engineering-work: forbidden actions must remain exact")
    if payload.get("additionalProperties") is not False:
        errors.append("route-engineering-work: routing decisions must reject additional properties")
    return errors


def _instruction_section(path: Path, heading: str) -> str | None:
    if not path.is_file():
        return None
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def validate_versioning_instructions() -> list[str]:
    agents_section = _instruction_section(ROOT / "AGENTS.md", "Versioning")
    claude_section = _instruction_section(ROOT / "CLAUDE.md", "Versioning")
    errors: list[str] = []
    if agents_section is None:
        errors.append("AGENTS.md: missing Versioning section")
    if claude_section is None:
        errors.append("CLAUDE.md: missing Versioning section")
    if agents_section is not None and claude_section is not None and agents_section != claude_section:
        errors.append("AGENTS.md and CLAUDE.md Versioning sections must match")
    required_terms = (
        "`VERSION`",
        "`VERSION_DESC.md`",
        "Semantic Versioning",
        "only the affected",
        "unmodified skills retain",
        "highest-impact",
        "Major:",
        "Minor:",
        "Patch:",
        "validate_repository.py",
    )
    if agents_section is not None:
        for term in required_terms:
            if term not in agents_section:
                errors.append(f"Versioning instructions must mention {term}")
    return errors


def validate_skill_package(skill_dir: Path) -> list[str]:
    errors = validate_frontmatter(skill_dir)
    for child in skill_dir.iterdir():
        if child.name not in ALLOWED_TOP_LEVEL:
            errors.append(f"{child.relative_to(ROOT)}: unsupported skill-package resource")
    for path in skill_dir.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            errors.append(f"{path.relative_to(ROOT)}: development or platform artifact inside skill package")
    return errors


def validate_script_references(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    text = skill_md.read_text(encoding="utf-8")
    errors: list[str] = []
    for reference in re.findall(r"python\s+[\"']?(scripts[/\\][A-Za-z0-9_-]+\.py)[\"']?", text):
        if not (skill_dir / reference.replace("\\", "/")).is_file():
            errors.append(f"{skill_md.relative_to(ROOT)}: references missing bundled script {reference}")
    return errors


def validate_retired_surfaces() -> list[str]:
    """Reject tracked-style platform surfaces while tolerating ignored bytecode caches."""
    errors: list[str] = []
    for relative_path in RETIRED_PATHS:
        path = ROOT / relative_path
        if path.is_file():
            errors.append(f"Retired platform artifact remains: {relative_path}")
        elif path.is_dir() and any("__pycache__" not in child.parts for child in path.rglob("*")):
            errors.append(f"Retired platform artifact remains: {relative_path}")
    return errors


def validate_legacy_plan_contracts() -> list[str]:
    """Keep v1-v4 plan formats out of active packages and fixtures.

    The one v4 string in the v5 negative test is intentional: it proves the
    canonical unsupported-contract diagnostic.
    """
    errors: list[str] = []
    ignored = {ROOT / "tests" / "skills" / "plan-change" / "test_v5_runtime.py"}
    pattern = re.compile(r"<!--\s*plan-(?:contract|validation):\s*[1-4](?:[; ]|-->)")
    for path in tracked_files():
        if path in ignored or "map-codebase" in path.parts:
            continue
        try:
            if pattern.search(path.read_text(encoding="utf-8")):
                errors.append(f"Legacy plan contract remains: {path.relative_to(ROOT)}")
        except UnicodeDecodeError:
            continue
    return errors


def main() -> int:
    skills = discover_skills()
    errors = ["No skills found under skills/<domain>/<skill>"] if not skills else []
    if not tracked_files():
        errors.append("Unable to enumerate Git-tracked repository files")
    errors.extend(validate_version())
    errors.extend(validate_version_description())
    errors.extend(validate_readme_release_link())
    errors.extend(validate_marketplace())
    errors.extend(validate_router_contract())
    errors.extend(validate_versioning_instructions())
    errors.extend(validate_domain_layout())
    for skill_dir in skills:
        errors.extend(validate_skill_package(skill_dir))
        errors.extend(validate_script_references(skill_dir))
    errors.extend(validate_retired_surfaces())
    errors.extend(validate_legacy_plan_contracts())
    for script in ("generate_plan_contract.py", "sync_plan_runtime.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validation" / script), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.extend(line for line in result.stderr.splitlines() if line)
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in sorted(set(errors)):
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Repository validation passed for {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
