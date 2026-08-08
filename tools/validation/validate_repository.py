#!/usr/bin/env python3
"""Validate the standalone skill repository."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from measure_context_load import validate_report as validate_context_load_report  # noqa: E402

from tools.skill_protocol import validate_manifest  # noqa: E402

SKILLS_ROOT = ROOT / "skills"
VERSION_PATH = ROOT / "VERSION"
README_PATH = ROOT / "README.md"
VERSION_DESCRIPTION_PATH = ROOT / "VERSION_DESC.md"
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
INVOCATION_POLICY_PATH = ROOT / "invocation-policy.json"
QUALITY_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "quality.yml"
ROUTER_SCHEMA_PATH = (
    ROOT / "skills" / "routing" / "route-work" / "schemas" / "route-validation.schema.json"
)
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
INVOCATION_MODES = {"user-invoked", "model-invoked", "both"}
SKILLS_CLI_VERSION = "1.5.21"
CERTIFIED_PLATFORMS = {
    "claude-code": {
        "metadata_surface": "SKILL.md frontmatter",
        "supports_implicit_policy": True,
        "supports_user_visibility": True,
    },
    "codex": {
        "metadata_surface": "agents/openai.yaml",
        "supports_implicit_policy": True,
        "supports_user_visibility": False,
    },
    "github-copilot": {
        "metadata_surface": "SKILL.md frontmatter",
        "supports_implicit_policy": True,
        "supports_user_visibility": True,
    },
}
FRONTMATTER_POLICY = {
    "user-invoked": {"disable-model-invocation": "true", "user-invocable": "true"},
    "model-invoked": {"disable-model-invocation": "false", "user-invocable": "false"},
    "both": {"disable-model-invocation": "false", "user-invocable": "true"},
}
LATEST_RELEASE_BADGE_RE = re.compile(
    r"\[!\[Latest Release\]\((?P<badge_url>[^)]+)\)\]\((?P<target_url>[^)]+)\)"
)
LATEST_RELEASE_URL = "https://github.com/akshay-diwadkar/skills/releases/latest"
MARKDOWN_LINK_RE = re.compile(
    r"!?\[[^\]]*\]\((?:<(?P<bracketed>[^>]+)>|(?P<plain>[^)\s]+))(?:\s+['\"][^)]*['\"])?\)"
)
EXPECTED_MARKETPLACE_GROUPS = {
    "engineering-skills": {
        "./skills/engineering/audit-codebase",
        "./skills/engineering/design-codebase",
        "./skills/engineering/diagram-codebase",
        "./skills/engineering/implement-plan",
        "./skills/engineering/map-codebase",
        "./skills/engineering/optimize-codebase",
        "./skills/engineering/plan-change",
        "./skills/engineering/raise-issue",
        "./skills/engineering/scope-issue",
    },
    "routing-skills": {
        "./skills/routing/route-work",
    },
    "research-skills": {
        "./skills/research/ideate",
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
    "raise-issue",
    "ideate",
}
ROUTER_FIELDS = {
    "valid",
    "workflow",
    "errors",
    "warnings",
    "route_handoff",
}
ROUTER_ISSUE_FIELDS = {"code", "skill", "requires", "message"}
DEFERRED_CONTEXT_SKILLS = {"map-codebase"}
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
    "skill-protocol.json",
    "agents",
}
FORBIDDEN_PARTS = {"evals", "fixtures", "__pycache__"}
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
        if skill.is_dir() and (skill / "SKILL.md").is_file()
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
    rel_md = skill_md.relative_to(ROOT) if skill_md.is_relative_to(ROOT) else skill_md
    rel_dir = skill_dir.relative_to(ROOT) if skill_dir.is_relative_to(ROOT) else skill_dir
    if not skill_md.is_file():
        return [f"{rel_dir}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{rel_md}: missing YAML frontmatter"]
    frontmatter = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    version = re.search(r"^version:\s*(.+)$", frontmatter, re.MULTILINE)
    errors: list[str] = []
    if not name or name.group(1).strip() != skill_dir.name:
        errors.append(f"{rel_md}: frontmatter name must match the skill directory")
    if not description or not description.group(1).strip():
        errors.append(f"{rel_md}: frontmatter description is required")
    if not version:
        errors.append(f"{rel_md}: frontmatter version is required")
    elif not SEMVER_RE.fullmatch(version.group(1).strip()):
        errors.append(
            f"{rel_md}: version "
            f"{version.group(1).strip()!r} is not valid Semantic Versioning"
        )

    top_keys = re.findall(r"^([a-zA-Z0-9_-]+):", frontmatter, re.MULTILINE)
    expected_keys = [
        "name",
        "description",
        "version",
        "metadata",
        "disable-model-invocation",
        "user-invocable",
    ]
    if top_keys != expected_keys:
        errors.append(
            f"{rel_md}: frontmatter keys must be ordered as {expected_keys}"
        )

    metadata_match = re.search(
        r"^metadata:\s*\n(?P<body>(?:^[ \t]+[^\n]*(?:\n|$))*)",
        frontmatter,
        re.MULTILINE,
    )
    if metadata_match:
        meta_keys = re.findall(
            r"^[ \t]+([a-zA-Z0-9_-]+):", metadata_match.group("body"), re.MULTILINE
        )
        if not meta_keys or meta_keys[0] != "invocation":
            errors.append(
                f"{rel_md}: metadata section must start with 'invocation'"
            )

    return errors


def _frontmatter(skill_dir: Path) -> str | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "---" not in text[4:]:
        return None
    return text.split("---", 2)[1]


def _frontmatter_field(frontmatter: str, field: str) -> str | None:
    match = re.search(rf"^{re.escape(field)}:\s*(\S.*?)\s*$", frontmatter, re.MULTILINE)
    return match.group(1) if match else None


def _metadata_field(frontmatter: str, field: str) -> str | None:
    metadata = re.search(
        r"^metadata:\s*\n(?P<body>(?:^[ \t]+[^\n]*(?:\n|$))*)",
        frontmatter,
        re.MULTILINE,
    )
    if metadata is None:
        return None
    match = re.search(
        rf"^[ \t]+{re.escape(field)}:\s*(\S.*?)\s*$",
        metadata.group("body"),
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _load_json_object(path: Path, label: str) -> tuple[dict[str, object] | None, list[str]]:
    if not path.is_file():
        return None, [f"Missing {label}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"{label}: invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"{label}: root must be an object"]
    return payload, []


def derive_invocation_safety_capabilities(skill_dir: Path) -> set[str]:
    """Derive capabilities that must never be exposed through implicit invocation."""
    capabilities: set[str] = set()
    manifest_path = skill_dir / "skill-protocol.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            manifest = {}
        if isinstance(manifest, dict):
            phases = manifest.get("phases", {})
            if isinstance(phases, dict):
                for phase in phases.values():
                    if not isinstance(phase, dict):
                        continue
                    writes = phase.get("allowed_writes", [])
                    if isinstance(writes, list) and "{repo_root}" in writes:
                        capabilities.add("repository-write")
            artifacts = manifest.get("artifacts", [])
            if isinstance(artifacts, list) and any(
                isinstance(artifact, dict) and artifact.get("external") is True
                for artifact in artifacts
            ):
                capabilities.add("external-output")
            commands = manifest.get("commands", {})
            if isinstance(commands, dict) and any("publish" in str(name) for name in commands):
                capabilities.add("publication")

    scripts = skill_dir / "scripts"
    if scripts.is_dir() and any(
        any(token in path.stem for token in ("post_merge", "publish_"))
        for path in scripts.glob("*.py")
    ):
        capabilities.add("external-write")
    if skill_dir.name == "implement-plan":
        capabilities.add("implementation")
    return capabilities


def validate_skill_invocation_metadata(skill_dir: Path, mode: str) -> list[str]:
    relative = skill_dir.relative_to(ROOT) if skill_dir.is_relative_to(ROOT) else skill_dir
    prefix = f"{relative}/SKILL.md"
    frontmatter = _frontmatter(skill_dir)
    if frontmatter is None:
        return [f"{prefix}: cannot validate invocation metadata without frontmatter"]

    errors: list[str] = []
    actual_mode = _metadata_field(frontmatter, "invocation")
    if actual_mode != mode:
        errors.append(f"{prefix}: metadata.invocation must be {mode!r}")

    expected_frontmatter = FRONTMATTER_POLICY.get(mode)
    if expected_frontmatter is None:
        errors.append(f"{prefix}: unsupported invocation mode {mode!r}")
    else:
        for field, expected in expected_frontmatter.items():
            actual = _frontmatter_field(frontmatter, field)
            if actual != expected:
                errors.append(f"{prefix}: {field} must be {expected} for {mode}")

    agents_dir = skill_dir / "agents"
    openai_path = agents_dir / "openai.yaml"
    if not openai_path.is_file():
        errors.append(f"{relative}/agents/openai.yaml: missing Codex invocation policy")
    else:
        text = openai_path.read_text(encoding="utf-8")
        match = re.fullmatch(
            r"policy:\s*\n  allow_implicit_invocation:\s*(true|false)\s*\n?",
            text,
        )
        if match is None:
            errors.append(f"{relative}/agents/openai.yaml: unsupported or malformed policy")
        else:
            expected = "false" if mode == "user-invoked" else "true"
            if match.group(1) != expected:
                errors.append(
                    f"{relative}/agents/openai.yaml: allow_implicit_invocation must be {expected} for {mode}"
                )
    if agents_dir.is_dir():
        unexpected = sorted(
            path.relative_to(skill_dir).as_posix()
            for path in agents_dir.rglob("*")
            if path.is_file() and path != openai_path
        )
        for path in unexpected:
            errors.append(f"{relative}/{path}: unsupported provider metadata")

    dangerous = derive_invocation_safety_capabilities(skill_dir)
    if dangerous and mode != "user-invoked":
        errors.append(
            f"{prefix}: {mode} conflicts with authority-required capabilities: "
            + ", ".join(sorted(dangerous))
        )
    if mode == "model-invoked":
        manifest_path = skill_dir / "skill-protocol.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                manifest = {}
            phases = manifest.get("phases", {}) if isinstance(manifest, dict) else {}
            writes = [
                value
                for phase in phases.values()
                if isinstance(phase, dict)
                for value in phase.get("allowed_writes", [])
            ] if isinstance(phases, dict) else []
            if writes:
                errors.append(f"{prefix}: model-invoked protocol phases must be read-only")
    return errors


def validate_invocation_policy(
    path: Path | None = None,
    skill_dirs: list[Path] | None = None,
) -> list[str]:
    path = path or INVOCATION_POLICY_PATH
    skill_dirs = skill_dirs or discover_skills()
    label = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    payload, errors = _load_json_object(path, label)
    if payload is None:
        return errors

    if set(payload) != {"schema_version", "certified_platforms", "skills"}:
        errors.append(f"{label}: fields must be schema_version, certified_platforms, and skills")
    if payload.get("schema_version") != 1:
        errors.append(f"{label}: schema_version must be 1")
    if payload.get("certified_platforms") != CERTIFIED_PLATFORMS:
        errors.append(f"{label}: certified_platforms must match the supported provider adapters")

    modes = payload.get("skills")
    if not isinstance(modes, dict) or not all(
        isinstance(name, str) and isinstance(mode, str) for name, mode in modes.items()
    ):
        errors.append(f"{label}: skills must map skill names to invocation modes")
        return errors

    discovered = {skill.name: skill for skill in skill_dirs}
    if set(modes) != set(discovered):
        missing = sorted(set(discovered) - set(modes))
        stale = sorted(set(modes) - set(discovered))
        if missing:
            errors.append(f"{label}: missing skills: {missing}")
        if stale:
            errors.append(f"{label}: references unknown skills: {stale}")
    for name, mode in modes.items():
        if mode not in INVOCATION_MODES:
            errors.append(f"{label}: {name} has unsupported invocation mode {mode!r}")
        elif name in discovered:
            errors.extend(validate_skill_invocation_metadata(discovered[name], mode))
    return errors


def validate_certified_platform_coverage(
    readme_path: Path | None = None,
    workflow_path: Path | None = None,
) -> list[str]:
    """Keep documented invocation support and the CI installation matrix aligned."""
    readme_path = readme_path or README_PATH
    workflow_path = workflow_path or QUALITY_WORKFLOW_PATH
    errors: list[str] = []
    expected = set(CERTIFIED_PLATFORMS)

    if not readme_path.is_file():
        errors.append("Missing README.md")
    else:
        text = readme_path.read_text(encoding="utf-8")
        match = re.search(r"^Certified agent names are (?P<names>.+?)\. For example:$", text, re.MULTILINE)
        names = set(re.findall(r"`([^`]+)`", match.group("names"))) if match else set()
        if names != expected:
            errors.append(f"README.md: certified agent names must be exactly {sorted(expected)}")

    if not workflow_path.is_file():
        errors.append("Missing .github/workflows/quality.yml")
    else:
        text = workflow_path.read_text(encoding="utf-8")
        match = re.search(r"^\s*agent:\s*\[([^]]+)\]\s*$", text, re.MULTILINE)
        names = {name.strip() for name in match.group(1).split(",")} if match else set()
        if names != expected:
            errors.append(
                ".github/workflows/quality.yml: Skills CLI agent matrix must match certified platforms"
            )
        if f"skills@{SKILLS_CLI_VERSION}" not in text:
            errors.append(
                f".github/workflows/quality.yml: grouped discovery must pin skills@{SKILLS_CLI_VERSION}"
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
        errors.append("route-work: validation result properties must remain exact")
        return errors
    if not isinstance(required, list) or set(required) != ROUTER_FIELDS:
        errors.append("route-work: every validation result property must remain required")
    if properties["valid"].get("type") != "boolean":
        errors.append("route-work: valid must be a boolean")
    workflow = properties.get("workflow")
    if (
        not isinstance(workflow, dict)
        or workflow.get("type") != "array"
        or not isinstance(workflow.get("items"), dict)
        or workflow["items"].get("$ref") != "#/$defs/skill"
    ):
        errors.append("route-work: workflow must be an array of routed skills")
    for field in ("errors", "warnings"):
        issues = properties.get(field)
        if (
            not isinstance(issues, dict)
            or issues.get("type") != "array"
            or not isinstance(issues.get("items"), dict)
            or issues["items"].get("$ref") != "#/$defs/issue"
        ):
            errors.append(f"route-work: {field} must be an array of validation issues")
    if properties.get("route_handoff", {}).get("type") != "string":
        errors.append("route-work: route_handoff must be a string")
    if not isinstance(definitions, dict):
        errors.append("route-work: validation schema must define routed skills")
    else:
        skill = definitions.get("skill")
        skill_enum = skill.get("enum") if isinstance(skill, dict) else None
        if not isinstance(skill_enum, list) or set(skill_enum) != ROUTED_SKILLS:
            errors.append("route-work: routed skill enum must remain exact")
        issue = definitions.get("issue")
        issue_props = issue.get("properties") if isinstance(issue, dict) else None
        if (
            not isinstance(issue, dict)
            or not isinstance(issue_props, dict)
            or set(issue_props) != ROUTER_ISSUE_FIELDS
        ):
            errors.append("route-work: validation issue definition must remain exact")
    if payload.get("additionalProperties") is not False:
        errors.append("route-work: validation results must reject additional properties")
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


VERSIONING_DELEGATE_HEADING = "Repository Changes"
VERSIONING_AUTHORITY_PATH = ROOT / "REPO_VERSIONING.md"
VERSIONING_REQUIRED_TERMS = (
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


def _versioning_delegate_section(path: Path) -> str | None:
    for heading in (VERSIONING_DELEGATE_HEADING, "Versioning"):
        section = _instruction_section(path, heading)
        if section is not None:
            return section
    return None


def validate_versioning_instructions() -> list[str]:
    agents_section = _versioning_delegate_section(ROOT / "AGENTS.md")
    claude_section = _versioning_delegate_section(ROOT / "CLAUDE.md")
    errors: list[str] = []
    if agents_section is None:
        errors.append(f"AGENTS.md: missing {VERSIONING_DELEGATE_HEADING} section")
    if claude_section is None:
        errors.append(f"CLAUDE.md: missing {VERSIONING_DELEGATE_HEADING} section")
    if agents_section is not None and claude_section is not None and agents_section != claude_section:
        errors.append(
            f"AGENTS.md and CLAUDE.md {VERSIONING_DELEGATE_HEADING} sections must match"
        )
    for label, section in (("AGENTS.md", agents_section), ("CLAUDE.md", claude_section)):
        if section is not None and "REPO_VERSIONING.md" not in section:
            errors.append(f"{label}: {VERSIONING_DELEGATE_HEADING} must reference REPO_VERSIONING.md")
    if not VERSIONING_AUTHORITY_PATH.is_file():
        errors.append("REPO_VERSIONING.md: missing versioning authority file")
        return errors
    authority_text = VERSIONING_AUTHORITY_PATH.read_text(encoding="utf-8")
    authority_lower = authority_text.lower()
    for term in VERSIONING_REQUIRED_TERMS:
        if term.lower() not in authority_lower:
            errors.append(f"REPO_VERSIONING.md must mention {term}")
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


def validate_markdown_references(skill_dir: Path) -> list[str]:
    """Validate local Markdown targets and direct progressive-disclosure links."""
    errors: list[str] = []
    skill_root = skill_dir.resolve()
    repository_root = ROOT.resolve()
    skill_md = skill_dir / "SKILL.md"
    directly_linked: set[Path] = set()

    for document in sorted(skill_dir.rglob("*.md")):
        if "__pycache__" in document.parts:
            continue
        text = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group("bracketed") or match.group("plain")
            if raw_target.startswith("#"):
                continue
            parsed = urlsplit(raw_target)
            if parsed.scheme or parsed.netloc:
                continue
            relative = unquote(parsed.path).replace("\\", "/")
            if not relative:
                continue
            target = (document.parent / relative).resolve()
            label = document.relative_to(ROOT)
            if not target.is_relative_to(repository_root):
                errors.append(f"{label}: local Markdown link escapes the repository: {raw_target}")
                continue
            if document == skill_md and not target.is_relative_to(skill_root):
                errors.append(f"{label}: SKILL.md link escapes its skill package: {raw_target}")
                continue
            if not target.exists():
                errors.append(f"{label}: local Markdown link target does not exist: {raw_target}")
                continue
            if document == skill_md:
                directly_linked.add(target)

    references_dir = skill_dir / "references"
    if references_dir.is_dir():
        for reference in sorted(references_dir.rglob("*.md")):
            if reference.resolve() not in directly_linked:
                errors.append(
                    f"{skill_md.relative_to(ROOT)}: reference is not linked directly: "
                    f"{reference.relative_to(skill_dir).as_posix()}"
                )
    return errors


def validate_skill_protocol(skill_dir: Path) -> list[str]:
    """Validate the required common CLI contract for executable skills."""
    manifest_path = skill_dir / "skill-protocol.json"
    scripts_dir = skill_dir / "scripts"
    executable = scripts_dir.is_dir() and any(
        path.name != "__init__.py" and "__pycache__" not in path.parts
        for path in scripts_dir.rglob("*.py")
    )
    if not manifest_path.exists():
        return [f"{skill_dir.relative_to(ROOT)}: executable skill is missing skill-protocol.json"] if executable else []
    cli_path = scripts_dir / "cli.py"
    fallback_path = scripts_dir / "_skill_protocol_runtime.py"
    diagnostic_path = scripts_dir / "_diagnostic_contract.py"
    errors: list[str] = []
    if not cli_path.is_file():
        errors.append("executable skill must expose scripts/cli.py")
    if not fallback_path.is_file():
        errors.append("executable skill must package scripts/_skill_protocol_runtime.py")
    elif fallback_path.read_bytes() != (ROOT / "tools" / "skill_protocol" / "runtime.py").read_bytes():
        errors.append("packaged common CLI runtime is stale")
    if not diagnostic_path.is_file():
        errors.append("executable skill must package scripts/_diagnostic_contract.py")
    elif diagnostic_path.read_bytes() != (ROOT / "tools" / "diagnostics" / "runtime.py").read_bytes():
        errors.append("packaged diagnostic runtime is stale")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{manifest_path.relative_to(ROOT)}: invalid JSON: {exc}"]
    errors.extend(validate_manifest(payload, skill_dir=skill_dir))
    if isinstance(payload, dict) and payload.get("skill") != skill_dir.name:
        errors.append("manifest skill must match the installed skill directory")
    return [f"{manifest_path.relative_to(ROOT)}: {error}" for error in sorted(set(errors))]


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
    errors.extend(validate_invocation_policy(skill_dirs=skills))
    errors.extend(validate_certified_platform_coverage())
    errors.extend(validate_router_contract())
    errors.extend(validate_versioning_instructions())
    errors.extend(validate_domain_layout())
    errors.extend(validate_context_load_report(excluded_skills=DEFERRED_CONTEXT_SKILLS))
    for skill_dir in skills:
        errors.extend(validate_skill_package(skill_dir))
        errors.extend(validate_script_references(skill_dir))
        errors.extend(validate_markdown_references(skill_dir))
        errors.extend(validate_skill_protocol(skill_dir))
    errors.extend(validate_retired_surfaces())
    errors.extend(validate_legacy_plan_contracts())
    for script in (
        "generate_plan_contract.py",
        "sync_diagnostic_runtime.py",
        "sync_plan_runtime.py",
        "sync_classification_runtime.py",
        "sync_skill_protocol_runtime.py",
    ):
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
