"""Compatibility registry for the independent realistic fixture emitters."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in {None, ""}:
    # Keep the documented module invocation canonical, while making this
    # thin fixture entry point safe for local diagnosis as well.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.generators.realistic.billing import emit as emit_billing
from benchmarks.generators.realistic.portal import emit as emit_portal
from benchmarks.generators.realistic.telemetry import emit as emit_telemetry
from benchmarks.generators.realistic.telemetry import emit_scale_stress

Emitter = Callable[[Path], None]
REGISTRY: dict[str, Emitter] = {
    "schema-migration-service": emit_billing,
    "plugin-workspace": emit_portal,
    "component-pipeline": emit_telemetry,
    "resolver-scale-stress": emit_scale_stress,
}


def generate(fixture_id: str, output: Path) -> None:
    """Generate exactly one named archetype into an empty output directory."""
    try:
        REGISTRY[fixture_id](output)
    except KeyError as exc:
        raise ValueError(f"unknown realistic fixture: {fixture_id}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", choices=sorted(REGISTRY))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    generate(args.fixture, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
