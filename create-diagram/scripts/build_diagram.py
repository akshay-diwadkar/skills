"""Build a create-diagram HTML file from a JSON payload.

Usage:
    python scripts/build_diagram.py --data payload.json --output diagram.html [--overwrite]

Payload shape:
    {
      "diagram": { ...DIAGRAM_DATA... },
      "metadata": { ...agent-metadata... }
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _diagram_utils import replace_agent_metadata, replace_js_assignment


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "html-excalidraw-template.html"


def build_diagram(payload_path, output_path, overwrite=False):
    payload_path = Path(payload_path)
    output_path = Path(output_path)

    if not payload_path.exists():
        raise FileNotFoundError(f"Payload file not found: {payload_path}")
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template file not found: {TEMPLATE_PATH}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output_path}. Pass --overwrite to replace it.")
    if output_path.resolve() == TEMPLATE_PATH.resolve():
        raise ValueError("Output path must not be the canonical template file.")

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    diagram = payload.get("diagram")
    metadata = payload.get("metadata")
    if not isinstance(diagram, dict):
        raise ValueError('Payload must contain an object field named "diagram".')
    if not isinstance(metadata, dict):
        raise ValueError('Payload must contain an object field named "metadata".')

    diagram_literal = (
        "const DIAGRAM_DATA = "
        + json.dumps(diagram, indent=2, ensure_ascii=False)
        + ";"
    )
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = replace_js_assignment(html, "DIAGRAM_DATA", diagram_literal)
    html = replace_agent_metadata(html, metadata)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build create-diagram HTML from a JSON payload.")
    parser.add_argument("--data", required=True, help="Path to payload JSON.")
    parser.add_argument("--output", required=True, help="Path to output .html file.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        output = build_diagram(args.data, args.output, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Written: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
