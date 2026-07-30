from __future__ import annotations

import json

from .run_full import _runner, write_report


def main() -> int:
    runner = _runner()
    result = runner.evaluate("representative")
    write_report(result, "representative", runner)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
