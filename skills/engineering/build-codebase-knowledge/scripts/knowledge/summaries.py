"""Evidence-backed summary generator for context.md and architecture.md."""

from __future__ import annotations

from typing import Any


def format_context_md(
    revision: str,
    subsystems: dict[str, list[str]],
    languages: list[str],
    entry_points: list[dict[str, Any]],
    commands: list[dict[str, str]],
    freshness_status: str = "fresh",
    unknowns: list[str] | None = None,
) -> str:
    """Format evidence-backed context.md document (Target <= 120 lines)."""
    lines = [
        "# Repository Context",
        "",
        f"Status: {freshness_status}",
        f"Revision: {revision}",
        "Source truth: repository files",
        "",
        "## Purpose",
        f"- Repository containing {len(subsystems)} subsystem(s) and structured code modules.",
        "",
        "## Languages & Frameworks",
    ]

    if languages:
        for lang in sorted(languages):
            lines.append(f"- {lang}")
    else:
        lines.append("- Observed: Standard multi-language codebase")

    lines.extend(
        [
            "",
            "## Subsystems & Components",
        ]
    )
    for sub in sorted(subsystems.keys()):
        paths = subsystems[sub]
        sample = paths[0] if paths else sub
        lines.append(f"- {sub}: `{sample}` ({len(paths)} files)")

    lines.extend(
        [
            "",
            "## Primary Entry Points",
        ]
    )
    if entry_points:
        for ep in sorted(entry_points, key=lambda e: e["path"])[:5]:
            lines.append(f"- Entry point: `{ep['path']}:{ep.get('symbol', 'main')}`")
    else:
        lines.append("- Observed: No explicit single entry point detected")

    lines.extend(
        [
            "",
            "## Evidence-Backed Commands",
        ]
    )
    if commands:
        for cmd in sorted(commands, key=lambda c: c["kind"]):
            lines.append(f"- {cmd['kind'].capitalize()}: `{cmd['cmd']}` (source: `{cmd['source']}`)")
    else:
        lines.append("- Observed: No build runner manifests detected (Makefile/package.json/pyproject.toml)")

    if unknowns:
        lines.extend(
            [
                "",
                "## Unresolved / Unknowns",
            ]
        )
        for unk in sorted(unknowns)[:3]:
            lines.append(f"- Unknown: {unk}")

    lines.extend(
        [
            "",
            "## Knowledge Artifact Detail",
            "- Architecture: `architecture.md`",
            "- Repository map: `repo-map.json`",
            "- Symbols: `symbols.json` (load only the selected shard)",
            "- Relationships: `relationships.json`",
        ]
    )

    return "\n".join(lines) + "\n"


def format_architecture_md(
    revision: str,
    subsystems: dict[str, list[str]],
    dependencies: list[dict[str, Any]],
    tests: list[dict[str, Any]],
    configurations: list[dict[str, Any]],
    freshness_status: str = "fresh",
) -> str:
    """Format evidence-backed architecture.md document (Target <= 220 lines)."""
    lines = [
        "# Architecture & Component Overview",
        "",
        f"Status: {freshness_status}",
        f"Revision: {revision}",
        "",
        "## Component Subsystem Matrix",
        "",
        "| Subsystem | File Count | Sample File | Role |",
        "|---|---|---|---|",
    ]

    for sub in sorted(subsystems.keys()):
        paths = subsystems[sub]
        sample = paths[0] if paths else sub
        lines.append(f"| {sub} | {len(paths)} | `{sample}` | Domain subsystem |")

    lines.extend(
        [
            "",
            "## Dependency Directions & Import Graph",
            f"- Total resolved internal dependency edges: {len(dependencies)}",
        ]
    )
    if dependencies:
        for dep in dependencies[:10]:
            lines.append(f"- `{dep['source']}` -> `{dep['target']}`")

    lines.extend(
        [
            "",
            "## Test Mappings",
            f"- Total mapped test suites: {len(tests)}",
        ]
    )
    if tests:
        for t in tests[:8]:
            targets_str = ", ".join(f"`{tgt}`" for tgt in t.get("targets", []))
            lines.append(f"- Test `{t['path']}` targets: {targets_str if targets_str else 'General test'}")

    lines.extend(
        [
            "",
            "## Configuration & Environment",
            f"- Total configuration manifests: {len(configurations)}",
        ]
    )
    if configurations:
        for cfg in configurations[:8]:
            lines.append(f"- Config: `{cfg['path']}`")

    lines.extend(
        [
            "",
            "## Critical Boundaries & Constraints",
            "- Source code files remain authoritative truth.",
            "- Knowledge index provides navigation assistance.",
        ]
    )

    return "\n".join(lines) + "\n"
