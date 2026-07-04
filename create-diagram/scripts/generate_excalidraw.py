"""Generate a .excalidraw file from a validated create-diagram HTML file."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from _diagram_utils import (
    compute_layout,
    extract_diagram_data,
    node_box,
    resolve_type,
    cluster_box,
    select_non_overlapping_routes,
)
import validate_diagram


NODE_STYLES = {
    "service": {"shape": "rectangle", "stroke": "#1a7abf", "fill": "#d0e8ff", "rounded": True},
    "external-system": {"shape": "rectangle", "stroke": "#bf7a1a", "fill": "#ffe0b2", "rounded": True},
    "database": {"shape": "rectangle", "stroke": "#1abf4a", "fill": "#d4f5d2", "rounded": False},
    "queue": {"shape": "rectangle", "stroke": "#2b7fb8", "fill": "#d8f0ff", "rounded": True},
    "file": {"shape": "rectangle", "stroke": "#b7831d", "fill": "#fff2c7", "rounded": False},
    "document": {"shape": "rectangle", "stroke": "#9a7a2f", "fill": "#fff8df", "rounded": False},
    "object-store": {"shape": "rectangle", "stroke": "#16856b", "fill": "#d9f7ef", "rounded": False},
    "actor": {"shape": "rectangle", "stroke": "#9a43b8", "fill": "#f8e0ff", "rounded": True},
    "process": {"shape": "rectangle", "stroke": "#3b78a8", "fill": "#dff0ff", "rounded": True},
    "decision": {"shape": "diamond", "stroke": "#bf6b1a", "fill": "#ffe6d1", "rounded": False},
    "event": {"shape": "ellipse", "stroke": "#5961bf", "fill": "#e5e7ff", "rounded": False},
    "concept": {"shape": "rectangle", "stroke": "#7a1abf", "fill": "#e8d5ff", "rounded": False},
    "failure-state": {"shape": "rectangle", "stroke": "#bf1a3a", "fill": "#ffd6e0", "rounded": False},
}

FIXED_TIMESTAMP = 1740000000000


def _seed(label):
    return int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF


def _roundness(style):
    return {"type": 3} if style.get("rounded") else None


def _style(node_type):
    return NODE_STYLES.get(resolve_type(node_type), NODE_STYLES["service"])


def _base_element(element_id, element_type, x, y, width, height, seed_label):
    return {
        "id": element_id,
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": _seed(seed_label),
        "version": 1,
        "versionNonce": _seed(seed_label + "-nonce"),
        "isDeleted": False,
        "boundElements": None,
        "updated": FIXED_TIMESTAMP,
        "link": None,
        "locked": False,
    }


def _wrap_text(text, width_chars):
    words = (text or "").split()
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > width_chars and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def build_node_shape(node, pos):
    style = _style(node.get("type", "service"))
    shape = _base_element(
        f"{node['id']}-shape",
        style["shape"],
        pos["x"],
        pos["y"],
        pos["w"],
        pos["h"],
        f"{node['id']}-shape",
    )
    shape.update({
        "strokeColor": style["stroke"],
        "backgroundColor": style["fill"],
        "roundness": _roundness(style),
        "boundElements": [{"type": "text", "id": f"{node['id']}-label"}],
    })
    return shape


def build_node_label(node, pos):
    title = node.get("label", "")
    desc = node.get("description", "")
    lines = [title]
    if desc:
        lines.append("")
        lines.extend(_wrap_text(desc, 34)[:3])
    text = "\n".join(lines)
    font_size = 18 if desc else 20
    height = max(26, (text.count("\n") + 1) * (font_size + 6))
    width = min(pos["w"] - 36, max(80, max(len(line) for line in lines) * font_size * 0.58))
    label = _base_element(
        f"{node['id']}-label",
        "text",
        pos["x"] + pos["w"] / 2 - width / 2,
        pos["y"] + pos["h"] / 2 - height / 2,
        width,
        height,
        f"{node['id']}-label",
    )
    label.update({
        "strokeColor": "#1e1e1e",
        "strokeWidth": 1,
        "text": text,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": f"{node['id']}-shape",
        "originalText": text,
        "autoResize": True,
        "lines": None,
    })
    return label


def build_edge_arrow(edge, route, edge_index):
    points = route["points"]
    min_x = min(p["x"] for p in points)
    min_y = min(p["y"] for p in points)
    max_x = max(p["x"] for p in points)
    max_y = max(p["y"] for p in points)
    arrow = _base_element(
        f"edge-{edge_index}",
        "arrow",
        min_x,
        min_y,
        max(max_x - min_x, 1),
        max(max_y - min_y, 1),
        f"edge-{edge_index}",
    )
    arrow.update({
        "strokeColor": "#5a4e3e",
        "strokeWidth": 2,
        "roundness": {"type": 2},
        "boundElements": [{"type": "text", "id": f"edge-{edge_index}-label"}],
        "points": [[p["x"] - min_x, p["y"] - min_y] for p in points],
        "startBinding": {"elementId": f"{edge['sourceId']}-shape", "focus": 0, "gap": 8},
        "endBinding": {"elementId": f"{edge['targetId']}-shape", "focus": 0, "gap": 8},
        "startArrowhead": None,
        "endArrowhead": "arrow",
    })
    return arrow


def build_edge_label(edge, route, edge_index):
    label_text = edge.get("label", "")
    box = route["labelBox"]
    label = _base_element(
        f"edge-{edge_index}-label",
        "text",
        box["x"],
        box["y"],
        box["w"],
        box["h"],
        f"edge-{edge_index}-label",
    )
    label.update({
        "strokeColor": "#5a4e3e",
        "strokeWidth": 1,
        "text": label_text,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": label_text,
        "autoResize": True,
        "lines": None,
    })
    return label


def build_cluster_background(cluster, nodes_by_id, positions):
    cid = cluster.get("id") or cluster.get("label")
    label = cluster.get("label", cid or "Cluster")
    box = cluster_box(cluster, nodes_by_id, positions)
    if not box:
        return []

    bg = _base_element(
        f"cluster-{cid}-bg",
        "rectangle",
        box["x"],
        box["y"],
        box["w"],
        box["h"],
        f"cluster-{cid}-bg",
    )
    bg.update({
        "strokeColor": "#b8ae9e",
        "backgroundColor": "#f1ede6",
        "strokeWidth": 1,
        "strokeStyle": "dashed",
        "roughness": 2,
        "roundness": {"type": 3},
    })

    text = _base_element(
        f"cluster-{cid}-label",
        "text",
        box["x"] + 14,
        box["y"] + 8,
        max(80, len(label) * 11),
        24,
        f"cluster-{cid}-label",
    )
    text.update({
        "strokeColor": "#5a4e3e",
        "strokeWidth": 1,
        "text": label,
        "fontSize": 18,
        "fontFamily": 1,
        "textAlign": "left",
        "verticalAlign": "top",
        "containerId": None,
        "originalText": label,
        "autoResize": True,
        "lines": None,
    })
    return [bg, text]


def derive_output_path(html_path):
    return Path(html_path).with_suffix(".excalidraw")


def validate_html_input(html_path):
    text = html_path.read_text(encoding="utf-8")
    errors = 0

    for issue in validate_diagram.check_structural_completeness(text):
        print(f"ERROR: {issue}", file=sys.stderr)
        errors += 1
    for issue in validate_diagram.check_embedded_assets(text):
        print(f"ERROR: {issue}", file=sys.stderr)
        errors += 1

    raw_block = validate_diagram.extract_raw_js_block(text, "DIAGRAM_DATA")
    if raw_block is None:
        print("ERROR: Could not find 'const DIAGRAM_DATA =' in file.", file=sys.stderr)
        errors += 1
        return False

    try:
        template_issues = validate_diagram.check_template_integrity(html_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        errors += 1
        template_issues = []
    for issue in template_issues:
        print(f"ERROR: {issue}", file=sys.stderr)
        errors += 1

    dangerous = validate_diagram.check_dangerous_js(raw_block)
    for line, desc in dangerous:
        print(
            f"ERROR: DIAGRAM_DATA line {line}: {desc}. The parser cannot handle this syntax.",
            file=sys.stderr,
        )
        errors += 1

    try:
        data = extract_diagram_data(text)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return False

    try:
        metadata = validate_diagram.extract_agent_metadata(text, required=True)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        errors += 1
        metadata = None
    validation_errors, _warnings = validate_diagram.validate(data, metadata)
    errors += validation_errors
    return errors == 0


def generate(input_html_path, overwrite=False):
    html_path = Path(input_html_path)
    if not html_path.exists():
        raise FileNotFoundError(f"Input not found: {html_path}")

    output_path = derive_output_path(html_path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output_path}. Pass --overwrite to replace it.")

    if not validate_html_input(html_path):
        raise ValueError("Input HTML validation failed. See errors above.")

    try:
        data = extract_diagram_data(html_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"Failed to extract diagram data: {exc}") from exc

    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    nodes_by_id = {node["id"]: node for node in nodes if node.get("id")}
    positions = compute_layout(data)
    edge_routes, route_error = select_non_overlapping_routes(edges, nodes_by_id, positions)
    if route_error:
        raise ValueError(f"Edge routing failed: {route_error}")

    elements = []

    for cluster in data.get("clusters") or []:
        elements.extend(build_cluster_background(cluster, nodes_by_id, positions))

    for node in nodes:
        pos = positions.get(node.get("id"))
        if not pos:
            print(f"WARNING: No position for node '{node.get('id')}'. Skipping.", file=sys.stderr)
            continue
        # Normalize width/height through the same box helper used by validation.
        pos = node_box(node, pos)
        elements.append(build_node_shape(node, pos))
        elements.append(build_node_label(node, pos))

    for index, route in enumerate(edge_routes or []):
        edge = route["edge"]
        elements.append(build_edge_arrow(edge, route, index))
        elements.append(build_edge_label(edge, route, index))

    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "create-diagram skill",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#faf6f0",
            "gridSize": None,
            "currentItemStrokeColor": "#1e1e1e",
            "currentItemBackgroundColor": "transparent",
            "currentItemFillStyle": "solid",
            "currentItemStrokeWidth": 2,
            "currentItemRoughness": 1,
            "currentItemOpacity": 100,
            "currentItemFontFamily": 1,
            "currentItemFontSize": 20,
            "currentItemTextAlign": "center",
            "previousGridSize": None,
            "theme": "light",
        },
        "files": {},
    }

    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    temp_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(output_path)
    print(f"Written: {output_path} ({len(elements)} elements)")
    return output_path


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Generate .excalidraw from validated diagram HTML.")
    parser.add_argument("html_path", help="Path to the generated diagram HTML.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing .excalidraw file.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        output = generate(args.html_path, overwrite=args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
