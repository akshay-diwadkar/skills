#!/usr/bin/env python3
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
for parent in SKILL_ROOT.parents:
    if (parent / "tools" / "skill_protocol" / "runtime.py").is_file():
        sys.path.insert(0, str(parent))
        from tools.skill_protocol.runtime import main

        raise SystemExit(
            main(
                ["--skill-dir", str(SKILL_ROOT), *sys.argv[1:]],
                cli_path=Path(__file__),
                expected_skill_dir=SKILL_ROOT,
            )
        )
raise SystemExit("skill protocol runtime unavailable")
