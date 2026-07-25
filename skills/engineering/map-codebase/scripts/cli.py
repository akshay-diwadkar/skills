#!/usr/bin/env python3
"""Unified CLI entry point for map-codebase."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_knowledge import build_knowledge
from link_agent_docs import ensure_agent_docs
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import format_human, resolve_task
from scaffold_github_workflow import (
    DEFAULT_BRANCH,
    DEFAULT_REPOSITORY,
    DEFAULT_RUNTIME_DIR,
    scaffold_github_workflow,
)
from validate_knowledge import validate_knowledge


def _main() -> int:
    parser = argparse.ArgumentParser(
        prog="map-codebase",
        description="Repository intelligence layer and deterministic task resolver.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build repository knowledge artifacts.")
    p_build.add_argument("--repo-root", default=".", help="Target repository root")
    p_build.add_argument("--output", "--knowledge-dir", help="Output knowledge directory")
    p_build.add_argument("--quiet", action="store_true", help="Suppress output")
    p_build.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

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
    repo_root = Path(args.repo_root).resolve()

    def finalize_agent_docs(result: dict[str, Any]) -> bool:
        try:
            result["agent_docs"] = ensure_agent_docs(repo_root, Path(args.output) if args.output else None)
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            print(f"Knowledge artifacts were created, but agent-document finalization failed: {exc}", file=sys.stderr)
            return False
        return True

    if args.command == "build":
        out = Path(args.output) if args.output else None
        res = build_knowledge(repo_root, out)
        if not finalize_agent_docs(res):
            return 1
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
        res = resolve_task(repo_root, t_str, out, selected_phase)
        if getattr(args, "format", "human") == "json":
            print(json.dumps(res, indent=2))
        else:
            print(format_human(res))
        return 0

    elif args.command == "refresh":
        out = Path(args.output) if args.output else None
        res = refresh_knowledge(repo_root, args.changed_file, out)
        if not finalize_agent_docs(res):
            return 1
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
    except (ValueError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
