#!/usr/bin/env python3
"""Preview or publish simple handoff issue sections through gh."""
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path

def normalize(value: str) -> str:
    value=value.strip().removesuffix('.git')
    match=re.search(r'github\.com[/:]([\w.-]+/[\w.-]+)$', value)
    if match: value=match.group(1)
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', value): raise ValueError('github_repo_url must be owner/repo or a GitHub URL')
    return value

def parse(path: Path):
    text=path.read_text(encoding='utf-8')
    if not text.startswith('<!-- audit-handoff: 1; sha256: '): raise ValueError('handoff is not sealed')
    parts=re.split(r'^## Issue [^:]+: ', text, flags=re.M)[1:]
    return [(part.split('\n',1)[0], part) for part in parts]

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--handoff',required=True,type=Path); p.add_argument('--github-repo-url',required=True); p.add_argument('--publish',action='store_true'); args=p.parse_args(argv)
    repo=normalize(args.github_repo_url); issues=parse(args.handoff)
    for title, body in issues:
        if not args.publish: print(f'DRY RUN create: {title}'); continue
        result=subprocess.run(['gh','issue','create','--repo',repo,'--title',title,'--body',body],capture_output=True,text=True)
        print(f"{'CREATED' if result.returncode == 0 else 'FAILED'}: {title} {result.stdout.strip() or result.stderr.strip()}")
    return 0
if __name__ == '__main__': raise SystemExit(main())
