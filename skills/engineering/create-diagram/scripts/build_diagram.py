"""Build a create-diagram HTML file from a JSON payload.

Usage:
    python scripts/build_diagram.py --data /absolute/path/to/payload.json --output /absolute/path/to/diagram.html [--create-dirs] [--overwrite]

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
import tempfile
from pathlib import Path

from _diagram_utils import replace_agent_metadata, replace_js_assignment, script_safe_json

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "html-diagram-template.html"
STYLE_PATH = SCRIPT_DIR.parent / "assets" / "css" / "style.css"
ROUGHJS_PATH = SCRIPT_DIR.parent / "assets" / "roughjs.js"


def html_safe_inline_asset(text):
    return text.replace("</", "<\\/")


def inline_runtime_assets(html):
    if not STYLE_PATH.exists():
        raise FileNotFoundError(f"Stylesheet not found: {STYLE_PATH}")
    if not ROUGHJS_PATH.exists():
        raise FileNotFoundError(f"RoughJS runtime not found: {ROUGHJS_PATH}")

    style = STYLE_PATH.read_text(encoding="utf-8")
    roughjs = html_safe_inline_asset(ROUGHJS_PATH.read_text(encoding="utf-8"))
    html = html.replace(
        '<link rel="stylesheet" href="css/style.css">',
        '<style id="create-diagram-style" data-inline-asset="css/style.css">\n'
        + style
        + "\n</style>",
    )
    html = html.replace(
        '<script src="roughjs.js"></script>',
        '<script id="create-diagram-roughjs" data-inline-asset="roughjs.js">\n'
        + roughjs
        + "\n</script>",
    )
    return html


def build_diagram(payload_path, output_path, overwrite=False, create_dirs=False):
    payload_path = Path(payload_path)
    output_path = Path(output_path)

    if not payload_path.exists():
        raise FileNotFoundError(f"Payload file not found: {payload_path}")
    if output_path.exists() and output_path.is_dir():
        raise IsADirectoryError(f"Output path is a directory, expected an .html file: {output_path}")
    if output_path.suffix.lower() != ".html":
        raise ValueError(f"Output path must end with .html: {output_path}")
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template file not found: {TEMPLATE_PATH}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output_path}. Pass --overwrite to replace it.")
    if output_path.resolve() == TEMPLATE_PATH.resolve():
        raise ValueError("Output path must not be the canonical template file.")
    if not output_path.parent.exists():
        if not create_dirs:
            raise FileNotFoundError(
                f"Output directory does not exist: {output_path.parent}. "
                "Pass --create-dirs after confirming directory creation."
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    diagram = payload.get("diagram")
    metadata = payload.get("metadata")
    if not isinstance(diagram, dict):
        raise ValueError('Payload must contain an object field named "diagram".')
    if not isinstance(metadata, dict):
        raise ValueError('Payload must contain an object field named "metadata".')

    diagram_literal = (
        "const DIAGRAM_DATA = "
        + script_safe_json(diagram, indent=2, ensure_ascii=False)
        + ";"
    )
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = inline_runtime_assets(html)
    html = replace_js_assignment(html, "DIAGRAM_DATA", diagram_literal)
    html = replace_agent_metadata(html, metadata)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(output_path.parent),
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(html)
        temp_path.replace(output_path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    return output_path


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Build create-diagram HTML from a JSON payload.")
    parser.add_argument("--data", required=True, help="Path to payload JSON.")
    parser.add_argument("--output", required=True, help="Path to output .html file.")
    parser.add_argument("--create-dirs", action="store_true", help="Create a missing output directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        output = build_diagram(args.data, args.output, args.overwrite, args.create_dirs)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Written: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
