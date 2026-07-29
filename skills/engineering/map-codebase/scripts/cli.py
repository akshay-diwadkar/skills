#!/usr/bin/env python3
"""Unified CLI entry point for map-codebase."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DEFAULT_REPOSITORY = "akshay-diwadkar/skills"
DEFAULT_RUNTIME_DIR = ".codebase-knowledge-runtime"
DEFAULT_BRANCH = "main"
MINIMUM_PYTHON = (3, 11)


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.match(r"(\d+(?:\.\d+)*)", value)
    return tuple(int(part) for part in numbers.group(1).split(".")) if numbers else ()


def _satisfies(installed: str, specifier: str) -> bool:
    current = _version_tuple(installed)
    for operator, expected_text in re.findall(r"(>=|<=|==|!=|>|<)\s*([0-9][^,;\s]*)", specifier):
        expected = _version_tuple(expected_text)
        if not expected:
            continue
        width = max(len(current), len(expected))
        left = current + (0,) * (width - len(current))
        right = expected + (0,) * (width - len(expected))
        comparisons = {
            ">=": left >= right,
            "<=": left <= right,
            "==": left == right,
            "!=": left != right,
            ">": left > right,
            "<": left < right,
        }
        if not comparisons[operator]:
            return False
    return True


def _requirements() -> list[tuple[str, str]]:
    requirements_path = SCRIPTS_DIR.parent / "requirements.txt"
    requirements = []
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
        if match:
            requirements.append((match.group(1), match.group(2)))
    return requirements


def run_doctor(
    repo_root_value: str | Path,
    version_lookup: Callable[[str], str] | None = None,
) -> int:
    """Run dependency-free preflight checks with actionable diagnostics."""
    lookup = version_lookup or importlib.metadata.version
    failures = False
    if sys.version_info[:2] >= MINIMUM_PYTHON:
        print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor} (requires >=3.11)")
    else:
        print(
            f"[FAIL] Python {sys.version_info.major}.{sys.version_info.minor} is unsupported; install Python 3.11 or newer."
        )
        failures = True

    try:
        repo_root = Path(repo_root_value).expanduser().resolve(strict=True)
        if not repo_root.is_dir():
            raise NotADirectoryError(repo_root)
        print(f"[OK] Repository root: {repo_root}")
    except (OSError, RuntimeError) as exc:
        print(f"[FAIL] Repository root cannot be resolved: {repo_root_value}")
        print(f"Fix: pass an existing directory with --repo-root. Details: {exc}")
        failures = True

    missing: list[str] = []
    incompatible: list[str] = []
    requirements = _requirements()
    for distribution, specifier in requirements:
        try:
            installed = lookup(distribution)
        except importlib.metadata.PackageNotFoundError:
            missing.append(distribution)
            continue
        if not _satisfies(installed, specifier):
            incompatible.append(f"{distribution} {installed} (requires {specifier})")
    if missing:
        print(f"[FAIL] Missing dependencies: {', '.join(missing)}")
        failures = True
    if incompatible:
        print(f"[FAIL] Incompatible dependencies: {', '.join(incompatible)}")
        failures = True
    if missing or incompatible:
        print(f'Fix: python -m pip install -r "{SCRIPTS_DIR.parent / "requirements.txt"}"')
    else:
        print(f"[OK] Dependencies: {len(requirements)} requirement(s) installed")
    return 1 if failures else 0


def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="map-codebase",
        description="Repository intelligence layer and deterministic task resolver.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # doctor intentionally has no imports from the rest of the skill.
    p_doctor = subparsers.add_parser("doctor", help="Check runtime prerequisites and repository path resolution.")
    p_doctor.add_argument("--repo-root", default=".", help="Target repository root")

    # build
    p_build = subparsers.add_parser("build", help="Build repository knowledge artifacts.")
    p_build.add_argument("--repo-root", default=".", help="Target repository root")
    p_build.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_build.add_argument("--quiet", action="store_true", help="Suppress output")
    p_build.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    p_build.add_argument("--dry-run", action="store_true", help="Show what would be indexed without writing")

    # status
    p_status = subparsers.add_parser("status", help="Check knowledge freshness status.")
    p_status.add_argument("--repo-root", default=".", help="Target repository root")
    p_status.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_status.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    # resolve
    p_resolve = subparsers.add_parser("resolve", help="Resolve natural language task.")
    p_resolve.add_argument("task", nargs="?", help="Task description string")
    p_resolve.add_argument("--task-file", help="File containing task description")
    p_resolve.add_argument("--repo-root", default=".", help="Target repository root")
    p_resolve.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_resolve.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    p_resolve.add_argument(
        "--phase", choices=["1", "2", "3", "all"], default="1", help="Return only the requested read phase"
    )
    p_resolve.add_argument(
        "--compact", action="store_true", help="Return minimal output: targets, confidence, and phase only"
    )
    p_resolve.add_argument(
        "--budget", type=int, default=0, help="Max tokens for returned targets (0 = unlimited)"
    )
    p_resolve.add_argument(
        "--record-analytics",
        action="store_true",
        help="Append a local analytics event (writes to the knowledge directory)",
    )

    # refresh
    p_refresh = subparsers.add_parser("refresh", help="Refresh knowledge artifacts incrementally.")
    p_refresh.add_argument("--repo-root", default=".", help="Target repository root")
    p_refresh.add_argument("--changed-file", action="append", default=[], help="Explicitly changed file path")
    p_refresh.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_refresh.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate knowledge status and conciseness.")
    p_validate.add_argument("--repo-root", default=".", help="Target repository root")
    p_validate.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_validate.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    # link-docs
    p_link = subparsers.add_parser("link-docs", help="Link knowledge docs in AGENTS.md / CLAUDE.md.")
    p_link.add_argument("--repo-root", default=".", help="Target repository root")
    p_link.add_argument("--output", "--knowledge-dir", help="Knowledge output directory")
    p_link.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    p_link.add_argument(
        "--create-missing",
        action="store_true",
        help="Deprecated; missing AGENTS.md and CLAUDE.md files are always created",
    )

    # generate-workflow is deliberately opt-in; no default knowledge command writes workflows.
    p_workflow = subparsers.add_parser("generate-workflow", help="Explicitly create a managed GitHub refresh workflow.")
    p_workflow.add_argument("--repo-root", default=".", help="Target repository root")
    p_workflow.add_argument("--revision", required=True, help="Required immutable 40-character runtime commit SHA")
    p_workflow.add_argument("--repository", default=DEFAULT_REPOSITORY, help="Runtime repository owner/name")
    p_workflow.add_argument("--runtime-dir", default=DEFAULT_RUNTIME_DIR, help="Relative runtime checkout directory")
    p_workflow.add_argument("--branch", default=DEFAULT_BRANCH, help="Branch that triggers refreshes")
    p_workflow.add_argument("--output", help="Repository-relative workflow output path")
    p_workflow.add_argument("--force", action="store_true", help="Replace a user-owned workflow")
    p_workflow.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    args = parser.parse_args()
    if args.command == "doctor":
        return run_doctor(args.repo_root)

    from finalize_knowledge import build_and_finalize, refresh_and_finalize
    from link_agent_docs import ensure_agent_docs
    from refresh_knowledge import check_freshness
    from resolve_task import compact_result, format_human, resolve_task
    from scaffold_github_workflow import scaffold_github_workflow
    from validate_knowledge import validate_knowledge

    repo_root = Path(args.repo_root).resolve()
    res: dict[str, Any]

    if args.command == "build":
        out = Path(args.output) if args.output else None
        if getattr(args, "dry_run", False):
            from knowledge.config import load_config, resolve_knowledge_directory
            from knowledge.discovery import discover_files
            config = load_config(repo_root)
            kdir = resolve_knowledge_directory(repo_root, out, config)
            included, generated, ignored = discover_files(repo_root, config, kdir)
            res = {
                "_meta": {"command": "build", "dry_run": True},
                "status": "dry-run",
                "files_to_index": len(included),
                "files_excluded": len(set(generated) | set(ignored)),
                "sample_files": sorted(included)[:20],
            }
        else:
            res = build_and_finalize(repo_root, out)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        elif not getattr(args, "quiet", False):
            print(f"Build completed: {res['files_indexed']} files, {res['symbols_indexed']} symbols indexed.")
        return 0

    elif args.command == "status":
        out = Path(args.output) if args.output else None
        st = check_freshness(repo_root, out)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(st, indent=2))
        else:
            print(f"Knowledge Status: {st['status']}")
            if "reason" in st:
                print(f"Details: {st['reason']}")
        return 0

    elif args.command == "resolve":
        t_str = args.task
        if args.task_file:
            t_str = Path(args.task_file).read_text(encoding="utf-8").strip()
        if not t_str:
            print("Error: task string or --task-file required", file=sys.stderr)
            return 1
        out = Path(args.output) if args.output else None
        selected_phase = args.phase if args.phase == "all" else int(args.phase)
        res = resolve_task(
            repo_root,
            t_str,
            out,
            selected_phase,
            budget=getattr(args, "budget", 0),
            record_analytics=getattr(args, "record_analytics", False),
        )
        if getattr(args, "compact", False):
            res = compact_result(res)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        else:
            print(format_human(res))
        return 0

    elif args.command == "refresh":
        out = Path(args.output) if args.output else None
        res = refresh_and_finalize(repo_root, args.changed_file, out)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        else:
            print(f"Refresh completed ({res['mode']} mode): status={res['status']}")
        return 0

    elif args.command == "validate":
        out = Path(args.output) if args.output else None
        res = validate_knowledge(repo_root, out)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        else:
            print(f"Validation status: {res['status']}")
            if res.get("warnings"):
                for w in res["warnings"]:
                    print(f"  Warning: {w}")
            if res.get("errors"):
                for e in res["errors"]:
                    print(f"  Error: {e}", file=sys.stderr)
        return 1 if res.get("errors") else 0

    elif args.command == "link-docs":
        out = Path(args.output) if args.output else None
        res = ensure_agent_docs(repo_root, out)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        else:
            if res["created"]:
                print(f"Created agent doc files referencing '{res['knowledge_path']}': {', '.join(res['created'])}")
            elif res["modified"]:
                print(f"Updated agent doc files referencing '{res['knowledge_path']}': {', '.join(res['modified'])}")
            elif res["skipped"]:
                print(f"Skipped opted-out agent doc files: {', '.join(res['skipped'])}")
            else:
                print("Agent doc files already up to date. No changes made.")
        return 0

    elif args.command == "generate-workflow":
        try:
            res = scaffold_github_workflow(
                repo_root,
                revision=args.revision,
                branch=args.branch,
                repository=args.repository,
                runtime_dir=args.runtime_dir,
                workflow_file=args.output,
                force=args.force,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        if args.format == "json":
            print(json.dumps(res, indent=2))
        elif res["status"] == "warning":
            print(f"Warning: {res['message']}")
        else:
            print(f"Workflow {res['status']}: {res['path']}")
        return 0 if res["status"] != "warning" else 1

    return 0


def main() -> int:
    """Convert expected operational failures into concise CLI diagnostics."""
    try:
        return _main()
    except (ValueError, FileNotFoundError, json.JSONDecodeError, OSError, RuntimeError) as exc:
        msg = str(exc)
        print(f"Error: {msg}", file=sys.stderr)
        if "missing" in msg.lower() and "build" not in msg.lower():
            print("  → Try: python scripts/cli.py build --repo-root <repo>", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
