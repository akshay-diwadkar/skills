#!/usr/bin/env python3
"""Unified CLI entry point for build-codebase-knowledge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmark_knowledge import BenchmarkRunner, format_human_report
from build_knowledge import build_knowledge
from link_agent_docs import link_agent_docs
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import format_human, resolve_task
from validate_knowledge import validate_knowledge

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="build-codebase-knowledge",
        description="Repository intelligence layer and deterministic task resolver."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build repository knowledge artifacts.")
    p_build.add_argument("--repo-root", default=".", help="Target repository root")
    p_build.add_argument("--output", help="Output directory")

    # status
    p_status = subparsers.add_parser("status", help="Check knowledge freshness status.")
    p_status.add_argument("--repo-root", default=".", help="Target repository root")
    p_status.add_argument("--output", help="Output directory")

    # resolve
    p_resolve = subparsers.add_parser("resolve", help="Resolve natural language task.")
    p_resolve.add_argument("task", nargs="?", help="Task description string")
    p_resolve.add_argument("--task-file", help="File containing task description")
    p_resolve.add_argument("--repo-root", default=".", help="Target repository root")
    p_resolve.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    # refresh
    p_refresh = subparsers.add_parser("refresh", help="Refresh knowledge artifacts incrementally.")
    p_refresh.add_argument("--repo-root", default=".", help="Target repository root")
    p_refresh.add_argument("--changed-file", action="append", default=[], help="Explicitly changed file path")
    p_refresh.add_argument("--output", help="Output directory")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate knowledge status and conciseness.")
    p_validate.add_argument("--repo-root", default=".", help="Target repository root")
    p_validate.add_argument("--output", help="Output directory")

    # benchmark
    p_benchmark = subparsers.add_parser("benchmark", help="Run benchmark evaluation suite.")
    p_benchmark.add_argument("--repo-root", default=".", help="Target repository root")
    p_benchmark.add_argument("--tasks", required=True, help="Path to benchmark tasks JSON file")
    p_benchmark.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    # link-docs
    p_link = subparsers.add_parser("link-docs", help="Link knowledge docs in AGENTS.md / CLAUDE.md.")
    p_link.add_argument("--repo-root", default=".", help="Target repository root")
    p_link.add_argument("--output", help="Knowledge output directory")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "build":
        out = Path(args.output).resolve() if args.output else None
        res = build_knowledge(repo_root, out)
        print(f"Build successful: indexed {res['files_indexed']} files, {res['symbols_indexed']} symbols.")
        return 0

    elif args.command == "status":
        out = Path(args.output).resolve() if args.output else None
        st = check_freshness(repo_root, out)
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
        res = resolve_task(repo_root, t_str)
        if args.format == "json":
            print(json.dumps(res, indent=2))
        else:
            print(format_human(res))
        return 0

    elif args.command == "refresh":
        out = Path(args.output).resolve() if args.output else None
        res = refresh_knowledge(repo_root, args.changed_file, out)
        print(f"Refresh finished ({res['mode']} mode): status={res['status']}")
        return 0

    elif args.command == "validate":
        out = Path(args.output).resolve() if args.output else None
        res = validate_knowledge(repo_root, out)
        print(f"Validation status: {res['status']}")
        if res.get("warnings"):
            for w in res["warnings"]:
                print(f"  Warning: {w}")
        if res.get("errors"):
            for e in res["errors"]:
                print(f"  Error: {e}")
            return 1
        return 0

    elif args.command == "benchmark":
        tasks_p = Path(args.tasks).resolve()
        runner = BenchmarkRunner(repo_root, tasks_p)
        res = runner.run_benchmark()
        if args.format == "json":
            print(json.dumps(res, indent=2))
        else:
            print(format_human_report(res))
        return 0

    elif args.command == "link-docs":
        out = Path(args.output).resolve() if args.output else None
        res = link_agent_docs(repo_root, out)
        if res["created"]:
            print(f"Created agent doc files referencing '{res['knowledge_path']}': {', '.join(res['created'])}")
        elif res["modified"]:
            print(f"Updated agent doc files referencing '{res['knowledge_path']}': {', '.join(res['modified'])}")
        else:
            print(f"Agent doc files already reference '{res['knowledge_path']}'. No changes made.")
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())
