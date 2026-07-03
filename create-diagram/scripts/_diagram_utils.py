"""Shared parsing, validation, and geometry helpers for create-diagram."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


CANONICAL_TYPES = frozenset({
    "service", "external-system", "database", "queue", "file", "document",
    "object-store", "actor", "process", "decision", "event", "concept",
    "failure-state",
})

TYPE_ALIASES = {
    "internal-service": "service",
    "data-store": "database",
}

VALID_FIDELITY = frozenset({"narrative-architecture", "exact-code-graph", "executive-concept-map"})
VALID_CONFIDENCE = frozenset({"observed", "inferred", "stated"})
VALID_CLUSTER_LAYOUTS = frozenset({"vertical", "circular"})
DEFAULT_STORAGE_KEY = "arch-overview-v1"

_GEOMETRY_CONFIG = json.loads(
    (Path(__file__).resolve().parent.parent / "assets" / "geometry-config.json").read_text(encoding="utf-8")
)

NODE_W = _GEOMETRY_CONFIG["NODE_W"]
NODE_H = _GEOMETRY_CONFIG["NODE_H"]
NODE_H_DESC = _GEOMETRY_CONFIG["NODE_H_DESC"]
TITLE_FONT_SIZE = _GEOMETRY_CONFIG["TITLE_FONT_SIZE"]
DESCRIPTION_FONT_SIZE = _GEOMETRY_CONFIG["DESCRIPTION_FONT_SIZE"]
MAX_DESC_CHARS = _GEOMETRY_CONFIG["MAX_DESC_CHARS"]
MAX_DESC_LINES = _GEOMETRY_CONFIG["MAX_DESC_LINES"]
CLUSTER_PAD = _GEOMETRY_CONFIG["CLUSTER_PAD"]
CLUSTER_LABEL_H = _GEOMETRY_CONFIG["CLUSTER_LABEL_H"]
NODE_GAP_Y = _GEOMETRY_CONFIG["NODE_GAP_Y"]
COLLISION_GAP = _GEOMETRY_CONFIG["COLLISION_GAP"]
CLUSTER_INTRUSION_GAP = _GEOMETRY_CONFIG["CLUSTER_INTRUSION_GAP"]
CLUSTER_GAP_X = _GEOMETRY_CONFIG["CLUSTER_GAP_X"]
CIRCULAR_RADIUS_FACTOR = _GEOMETRY_CONFIG["CIRCULAR_RADIUS_FACTOR"]
CIRCULAR_MIN_RADIUS = _GEOMETRY_CONFIG["CIRCULAR_MIN_RADIUS"]
EDGE_END_PAD = _GEOMETRY_CONFIG["EDGE_END_PAD"]
EDGE_NODE_CLEARANCE = _GEOMETRY_CONFIG["EDGE_NODE_CLEARANCE"]
EDGE_ENDPOINT_ALLOWANCE = _GEOMETRY_CONFIG["EDGE_ENDPOINT_ALLOWANCE"]
EDGE_SEGMENT_CLEARANCE = _GEOMETRY_CONFIG["EDGE_SEGMENT_CLEARANCE"]


def resolve_type(raw):
    return TYPE_ALIASES.get(raw, raw)


def _consume_js_string(text, start):
    quote = text[start]
    i = start + 1
    escape = False
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == quote:
            return i + 1
        i += 1
    return len(text)


def _consume_template_literal(text, start):
    i = start + 1
    escape = False
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == "`":
            return i + 1
        i += 1
    return len(text)


def _consume_js_comment(text, start):
    if text.startswith("//", start):
        end = text.find("\n", start + 2)
        return len(text) if end == -1 else end + 1
    if text.startswith("/*", start):
        end = text.find("*/", start + 2)
        return len(text) if end == -1 else end + 2
    return start


def extract_raw_js_block(text, var_name):
    """Extract the raw JS object literal assigned to `const var_name = {...};`."""
    pattern = re.compile(r"\bconst\s+" + re.escape(var_name) + r"\s*=\s*", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return None

    i = match.end()
    while i < len(text):
        if text[i] in " \t\r\n":
            i += 1
            continue
        if text.startswith("//", i) or text.startswith("/*", i):
            i = _consume_js_comment(text, i)
            continue
        break

    if i >= len(text) or text[i] != "{":
        return None

    brace_start = i
    depth = 0
    while i < len(text):
        ch = text[i]
        if ch in ("'", '"'):
            i = _consume_js_string(text, i)
            continue
        if ch == "`":
            i = _consume_template_literal(text, i)
            continue
        if text.startswith("//", i) or text.startswith("/*", i):
            i = _consume_js_comment(text, i)
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start:i + 1]
        i += 1
    return None


def replace_js_assignment(text, var_name, replacement):
    pattern = re.compile(r"\bconst\s+" + re.escape(var_name) + r"\s*=\s*", re.DOTALL)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Could not find const {var_name} =")
    raw = extract_raw_js_block(text[match.start():], var_name)
    if raw is None:
        raise ValueError(f"Could not parse {var_name} object literal")
    start = match.start()
    raw_start = text.find(raw, match.end())
    end = raw_start + len(raw)
    if end < len(text) and text[end] == ";":
        end += 1
    return text[:start] + replacement.strip() + text[end:]


def js_obj_to_json(raw):
    """Convert a limited JS object literal to valid JSON.

    The template contract deliberately uses JSON-like data: quoted or bare keys,
    strings, arrays, objects, numbers, booleans, null, comments, and trailing
    commas. Template literals and expressions remain unsupported.
    """
    result = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in ("'", '"'):
            quote = ch
            result.append('"')
            i += 1
            while i < len(raw):
                cur = raw[i]
                if cur == "\\":
                    result.append(cur)
                    i += 1
                    if i < len(raw):
                        result.append(raw[i])
                        i += 1
                elif cur == quote:
                    result.append('"')
                    i += 1
                    break
                elif quote == "'" and cur == '"':
                    result.append('\\"')
                    i += 1
                else:
                    result.append(cur)
                    i += 1
            continue
        if ch == "`":
            raise ValueError("template literal backtick strings are not supported in DIAGRAM_DATA")
        if text_comment := _consume_js_comment(raw, i):
            if text_comment != i:
                i = text_comment
                continue
        if ch in "{}[](),:":
            result.append(ch)
            i += 1
        elif ch in " \t\n\r":
            result.append(ch)
            i += 1
        elif re.match(r"[\w_$]", ch) and (
            i == 0 or (not re.match(r"[\w_$]", raw[i - 1]) and raw[i - 1] not in ".\"'")
        ):
            key_match = re.match(r"([\w_$-]+)\s*:", raw[i:])
            if key_match:
                result.append(json.dumps(key_match.group(1)))
                result.append(":")
                i += len(key_match.group(0))
            else:
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1

    converted = "".join(result)
    return re.sub(r",(\s*[}\]])", r"\1", converted)


def extract_diagram_data(text):
    raw = extract_raw_js_block(text, "DIAGRAM_DATA")
    if raw is None:
        raise ValueError("Could not find 'const DIAGRAM_DATA =' in file.")
    try:
        return json.loads(js_obj_to_json(raw))
    except ValueError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse DIAGRAM_DATA JSON: {exc}") from exc


def extract_agent_metadata(text):
    pattern = re.compile(
        r'<script\s+type="application/json"\s+id="agent-metadata">(.*?)</script>',
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return None
    content = match.group(1).strip()
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def replace_agent_metadata(text, metadata):
    pattern = re.compile(
        r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>',
        re.DOTALL,
    )
    block = (
        '<script type="application/json" id="agent-metadata">\n'
        + json.dumps(metadata, indent=2, ensure_ascii=False)
        + "\n</script>"
    )
    if not pattern.search(text):
        raise ValueError("Could not find agent-metadata script tag")
    return pattern.sub(block, text, count=1)


EVIDENCE_FILE_LINE = re.compile(r"^[\w/.+\\ -]+:\d+$")
EVIDENCE_FILE_RANGE = re.compile(r"^[\w/.+\\ -]+:\d+-\d+$")
EVIDENCE_USER_STATED = re.compile(r"^user-stated\b")


def evidence_quality(evidence):
    if not evidence:
        return "missing"
    if EVIDENCE_FILE_LINE.match(evidence):
        return None
    if EVIDENCE_FILE_RANGE.match(evidence):
        return None
    if EVIDENCE_USER_STATED.match(evidence):
        return None
    return "unusual format (expected file:line, file:start-end, or user-stated)"


def node_width(label, desc=None):
    label = label or ""
    desc = desc or ""
    label_w = len(label) * 18 + 88
    desc_w = min(len(desc), MAX_DESC_CHARS) * 10.6 + 76 if desc else 0
    return max(NODE_W, label_w, desc_w)


def node_height(node):
    if not node or not node.get("description"):
        return NODE_H
    approx_lines = math.ceil(len(node.get("description", "")) / 31)
    lines = min(approx_lines, MAX_DESC_LINES)
    return NODE_H_DESC + (lines - 1) * 30


def node_box(node, pos=None):
    pos = pos or node
    return {
        "x": float(pos.get("x", 0)),
        "y": float(pos.get("y", 0)),
        "w": float(pos.get("w", node_width(node.get("label", ""), node.get("description")))),
        "h": float(pos.get("h", node_height(node))),
    }


def nodes_with_partial_positions(nodes):
    partial = []
    for node in nodes or []:
        has_x = "x" in node and node.get("x") is not None
        has_y = "y" in node and node.get("y") is not None
        if has_x != has_y:
            partial.append(node.get("id") or node.get("label") or "?")
    return partial


def all_nodes_have_positions(nodes):
    nodes = nodes or []
    return bool(nodes) and all("x" in n and "y" in n and n.get("x") is not None and n.get("y") is not None for n in nodes)


def topological_order(node_ids, edges):
    remaining = list(node_ids)
    node_set = set(remaining)
    in_deg = {nid: 0 for nid in remaining}
    out = {nid: [] for nid in remaining}
    for edge in edges or []:
        src = edge.get("sourceId")
        tgt = edge.get("targetId")
        if src in node_set and tgt in node_set and src != tgt:
            out[src].append(tgt)
            in_deg[tgt] += 1
    queue = [nid for nid in remaining if in_deg[nid] == 0]
    result = []
    while queue:
        nid = queue.pop(0)
        result.append(nid)
        for tgt in out[nid]:
            in_deg[tgt] -= 1
            if in_deg[tgt] == 0:
                queue.append(tgt)
    for nid in remaining:
        if nid not in result:
            result.append(nid)
    return result


def compute_layout(data):
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    clusters = data.get("clusters") or []
    if all_nodes_have_positions(nodes):
        return {
            n["id"]: {
                "x": float(n["x"]),
                "y": float(n["y"]),
                "w": node_width(n.get("label", ""), n.get("description")),
                "h": node_height(n),
            }
            for n in nodes
            if n.get("id")
        }

    node_by_id = {n.get("id"): n for n in nodes if n.get("id")}
    positions = {}
    assigned = set()
    current_x = 60
    top_offset = 140

    for cluster in clusters:
        node_ids = [nid for nid in cluster.get("nodeIds", []) if nid in node_by_id and nid not in assigned]
        if not node_ids:
            continue
        assigned.update(node_ids)
        ordered_ids = topological_order(node_ids, edges)
        members = [node_by_id[nid] for nid in ordered_ids]
        layout = cluster.get("layout", "vertical")
        max_w = max([node_width(n.get("label", ""), n.get("description")) for n in members] + [NODE_W])

        if layout == "circular" and len(members) > 2:
            radius = max(CIRCULAR_MIN_RADIUS, len(members) * CIRCULAR_RADIUS_FACTOR)
            cluster_w = radius * 2 + max_w + CLUSTER_PAD * 4
            center_x = current_x + cluster_w / 2
            center_y = top_offset + CLUSTER_PAD + CLUSTER_LABEL_H + radius + NODE_H / 2
            for index, node in enumerate(members):
                angle = index / len(members) * 2 * math.pi - math.pi / 2
                w = node_width(node.get("label", ""), node.get("description"))
                h = node_height(node)
                positions[node["id"]] = {
                    "x": center_x + radius * math.cos(angle) - w / 2,
                    "y": center_y + radius * math.sin(angle) - h / 2,
                    "w": w,
                    "h": h,
                }
            current_x += cluster_w + CLUSTER_GAP_X
        else:
            left = current_x + CLUSTER_PAD
            cur_y = top_offset + CLUSTER_PAD + CLUSTER_LABEL_H
            for index, node in enumerate(members):
                w = node_width(node.get("label", ""), node.get("description"))
                h = node_height(node)
                positions[node["id"]] = {"x": left, "y": cur_y, "w": w, "h": h}
                if index < len(members) - 1:
                    next_id = ordered_ids[index + 1]
                    connecting = [
                        e for e in edges
                        if {e.get("sourceId"), e.get("targetId")} == {node["id"], next_id}
                    ]
                    max_label_w = max([edge_label_width(e.get("label", "")) for e in connecting] + [0])
                    label_gap = min(max(max_label_w * 1.2, 96), 320)
                    cur_y += h + max(NODE_GAP_Y, label_gap)
                else:
                    cur_y += h + NODE_GAP_Y
            current_x += max_w + CLUSTER_PAD * 2 + CLUSTER_GAP_X

    unclustered = [n for n in nodes if n.get("id") not in assigned]
    if unclustered:
        cur_y = top_offset + CLUSTER_PAD + CLUSTER_LABEL_H
        x = current_x + CLUSTER_PAD if positions else 60 + CLUSTER_PAD
        for node in unclustered:
            w = node_width(node.get("label", ""), node.get("description"))
            h = node_height(node)
            positions[node["id"]] = {"x": x, "y": cur_y, "w": w, "h": h}
            cur_y += h + NODE_GAP_Y

    return positions


def cluster_box(cluster, nodes_by_id, positions):
    members = []
    for node_id in cluster.get("nodeIds") or []:
        node = nodes_by_id.get(node_id)
        pos = positions.get(node_id)
        if node and pos:
            members.append(node_box(node, pos))
    if not members:
        return None
    min_x = min(m["x"] for m in members) - CLUSTER_PAD
    min_y = min(m["y"] for m in members) - CLUSTER_PAD - CLUSTER_LABEL_H
    max_x = max(m["x"] + m["w"] + 10 for m in members) + CLUSTER_PAD
    max_y = max(m["y"] + m["h"] + 10 for m in members) + CLUSTER_PAD
    return {"x": min_x, "y": min_y, "w": max_x - min_x, "h": max_y - min_y}


def edge_anchor(from_node, to_node, positions):
    a = node_box(from_node, positions[from_node["id"]])
    b = node_box(to_node, positions[to_node["id"]])
    acx = a["x"] + a["w"] / 2
    acy = a["y"] + a["h"] / 2
    bcx = b["x"] + b["w"] / 2
    bcy = b["y"] + b["h"] / 2
    dx = bcx - acx
    dy = bcy - acy
    if abs(dx) >= abs(dy):
        return {"x": a["x"] + a["w"] + EDGE_END_PAD, "y": acy} if dx >= 0 else {"x": a["x"] - EDGE_END_PAD, "y": acy}
    return {"x": acx, "y": a["y"] + a["h"] + EDGE_END_PAD} if dy >= 0 else {"x": acx, "y": a["y"] - EDGE_END_PAD}


def _i32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


def parallel_edge_offset(edge, edge_index, edges):
    same_pair = [
        (index, candidate) for index, candidate in enumerate(edges or [])
        if candidate.get("sourceId") == edge.get("sourceId") and candidate.get("targetId") == edge.get("targetId")
    ]
    pair_index = next((idx for idx, (index, _candidate) in enumerate(same_pair) if index == edge_index), 0)
    pair_offset = (pair_index - (len(same_pair) - 1) / 2) * 28
    key = f"{edge.get('sourceId')}->{edge.get('targetId')}"
    hashed = 0
    for ch in key:
        hashed = _i32((hashed << 5) - hashed + ord(ch))
    sign = 1 if hashed % 2 == 0 else -1
    return pair_offset + 18 * sign


def sample_curve(points, steps=12):
    if len(points) != 3:
        return points
    a, c, b = points
    samples = []
    for index in range(steps + 1):
        t = index / steps
        mt = 1 - t
        samples.append({
            "x": mt * mt * a["x"] + 2 * mt * t * c["x"] + t * t * b["x"],
            "y": mt * mt * a["y"] + 2 * mt * t * c["y"] + t * t * b["y"],
        })
    return samples


def edge_label_width(label):
    return max(64, len(label or "") * 13.2 + 30)


def edge_label_box(edge, x, y):
    width = edge_label_width(edge.get("label", ""))
    return {"x": x - width / 2, "y": y - 29, "w": width, "h": 34}


def edge_route(edge, edge_index, nodes_by_id, positions, edges):
    src = nodes_by_id.get(edge.get("sourceId"))
    tgt = nodes_by_id.get(edge.get("targetId"))
    if not src or not tgt or src["id"] not in positions or tgt["id"] not in positions:
        return None
    if src["id"] == tgt["id"]:
        box = node_box(src, positions[src["id"]])
        x1 = box["x"] + box["w"] + EDGE_END_PAD
        y1 = box["y"] + box["h"] * 0.35
        x2 = box["x"] + box["w"] + EDGE_END_PAD
        y2 = box["y"] + box["h"] * 0.65
        loop_x = box["x"] + box["w"] + 72
        points = [
            {"x": x1, "y": y1},
            {"x": loop_x, "y": box["y"] - 26},
            {"x": loop_x, "y": box["y"] + box["h"] + 26},
            {"x": x2, "y": y2},
        ]
        label_point = {"x": loop_x, "y": box["y"] + box["h"] / 2}
        return {
            "edge": edge,
            "src": src,
            "tgt": tgt,
            "points": points,
            "samples": points,
            "labelPoint": label_point,
            "labelBox": edge_label_box(edge, label_point["x"], label_point["y"]),
        }
    start = edge_anchor(src, tgt, positions)
    end = edge_anchor(tgt, src, positions)
    dx = end["x"] - start["x"]
    dy = end["y"] - start["y"]
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1:
        return None
    mid_x = (start["x"] + end["x"]) / 2
    mid_y = (start["y"] + end["y"]) / 2
    offset = max(-160, min(160, parallel_edge_offset(edge, edge_index, edges) + min(dist * 0.08, 32)))
    control = {"x": mid_x + dy / dist * offset, "y": mid_y - dx / dist * offset}
    points = [start, control, end]
    return {
        "edge": edge,
        "src": src,
        "tgt": tgt,
        "points": points,
        "samples": sample_curve(points),
        "labelPoint": control,
        "labelBox": edge_label_box(edge, control["x"], control["y"]),
    }


def route_from_points(edge, src, tgt, points, label_point=None):
    if label_point is None:
        label_point = route_midpoint(points)
    return {
        "edge": edge,
        "src": src,
        "tgt": tgt,
        "points": points,
        "samples": sample_polyline(points),
        "labelPoint": label_point,
        "labelBox": edge_label_box(edge, label_point["x"], label_point["y"]),
    }


def side_anchor(node, pos, side, pad=EDGE_END_PAD):
    box = node_box(node, pos)
    if side == "left":
        return {"x": box["x"] - pad, "y": box["y"] + box["h"] / 2}
    if side == "right":
        return {"x": box["x"] + box["w"] + pad, "y": box["y"] + box["h"] / 2}
    if side == "top":
        return {"x": box["x"] + box["w"] / 2, "y": box["y"] - pad}
    if side == "bottom":
        return {"x": box["x"] + box["w"] / 2, "y": box["y"] + box["h"] + pad}
    raise ValueError(f"Unknown side: {side}")


def route_midpoint(points):
    if not points:
        return {"x": 0, "y": 0}
    if len(points) == 1:
        return points[0]
    lengths = []
    total = 0
    for start, end in zip(points, points[1:]):
        length = distance(start, end)
        lengths.append(length)
        total += length
    if total == 0:
        return points[0]
    target = total / 2
    walked = 0
    for index, length in enumerate(lengths):
        if walked + length >= target:
            ratio = 0 if length == 0 else (target - walked) / length
            start = points[index]
            end = points[index + 1]
            return {"x": start["x"] + (end["x"] - start["x"]) * ratio,
                    "y": start["y"] + (end["y"] - start["y"]) * ratio}
        walked += length
    return points[-1]


def longest_segment_midpoint(points):
    best = None
    best_length = -1
    for start, end in zip(points, points[1:]):
        length = distance(start, end)
        if length > best_length:
            best_length = length
            best = {"x": (start["x"] + end["x"]) / 2, "y": (start["y"] + end["y"]) / 2}
    return best or route_midpoint(points)


def sample_polyline(points, steps_per_segment=8):
    samples = []
    if not points:
        return samples
    for start, end in zip(points, points[1:]):
        for index in range(steps_per_segment + 1):
            if samples and index == 0:
                continue
            ratio = index / steps_per_segment
            samples.append({
                "x": start["x"] + (end["x"] - start["x"]) * ratio,
                "y": start["y"] + (end["y"] - start["y"]) * ratio,
            })
    return samples or [points[0]]


def distance(a, b):
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def point_segment_distance(point, start, end):
    dx = end["x"] - start["x"]
    dy = end["y"] - start["y"]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return distance(point, start)
    t = max(0, min(1, ((point["x"] - start["x"]) * dx + (point["y"] - start["y"]) * dy) / length_sq))
    projection = {"x": start["x"] + t * dx, "y": start["y"] + t * dy}
    return distance(point, projection)


def orientation(a, b, c):
    value = (b["y"] - a["y"]) * (c["x"] - b["x"]) - (b["x"] - a["x"]) * (c["y"] - b["y"])
    if abs(value) < 1e-9:
        return 0
    return 1 if value > 0 else 2


def on_segment(a, b, c):
    return (
        min(a["x"], c["x"]) - 1e-9 <= b["x"] <= max(a["x"], c["x"]) + 1e-9
        and min(a["y"], c["y"]) - 1e-9 <= b["y"] <= max(a["y"], c["y"]) + 1e-9
    )


def segments_intersect(a1, a2, b1, b2):
    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_segment(a1, b1, a2):
        return True
    if o2 == 0 and on_segment(a1, b2, a2):
        return True
    if o3 == 0 and on_segment(b1, a1, b2):
        return True
    if o4 == 0 and on_segment(b1, a2, b2):
        return True
    return False


def segment_box_overlap(start, end, box, allowed_points=None, clearance=0):
    allowed_points = allowed_points or []
    expanded = expand_box(box, clearance)
    for sample in sample_polyline([start, end], 12):
        if not point_in_box(sample, expanded):
            continue
        if any(distance(sample, allowed) <= EDGE_ENDPOINT_ALLOWANCE for allowed in allowed_points):
            continue
        return True
    corners = [
        {"x": expanded["x"], "y": expanded["y"]},
        {"x": expanded["x"] + expanded["w"], "y": expanded["y"]},
        {"x": expanded["x"] + expanded["w"], "y": expanded["y"] + expanded["h"]},
        {"x": expanded["x"], "y": expanded["y"] + expanded["h"]},
    ]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        if segments_intersect(start, end, a, b):
            if any(
                distance(start, allowed) <= EDGE_ENDPOINT_ALLOWANCE
                or distance(end, allowed) <= EDGE_ENDPOINT_ALLOWANCE
                for allowed in allowed_points
            ):
                continue
            midpoint = {"x": (start["x"] + end["x"]) / 2, "y": (start["y"] + end["y"]) / 2}
            if any(distance(midpoint, allowed) <= EDGE_ENDPOINT_ALLOWANCE for allowed in allowed_points):
                continue
            return True
    return False


def route_segments(route):
    return list(zip(route.get("points", []), route.get("points", [])[1:]))


def routes_overlap(a, b):
    for a_start, a_end in route_segments(a):
        for b_start, b_end in route_segments(b):
            if not segments_intersect(a_start, a_end, b_start, b_end):
                if min(
                    point_segment_distance(a_start, b_start, b_end),
                    point_segment_distance(a_end, b_start, b_end),
                    point_segment_distance(b_start, a_start, a_end),
                    point_segment_distance(b_end, a_start, a_end),
                ) > EDGE_SEGMENT_CLEARANCE:
                    continue
            near_endpoint = False
            for pa in (a_start, a_end):
                for pb in (b_start, b_end):
                    if distance(pa, pb) <= EDGE_ENDPOINT_ALLOWANCE:
                        near_endpoint = True
            if near_endpoint:
                continue
            return True
    return False


def route_overlaps_box(route, box, allowed_points=None, clearance=0):
    for start, end in route_segments(route):
        if segment_box_overlap(start, end, box, allowed_points=allowed_points, clearance=clearance):
            return True
    return False


def route_label_overlaps_route(label_box, route):
    return route_overlaps_box(route, label_box, clearance=0)


def describe_route_conflict(route, node_boxes=None, accepted_routes=None):
    node_boxes = node_boxes or {}
    accepted_routes = accepted_routes or []
    edge = route.get("edge", {})
    src_id = edge.get("sourceId")
    tgt_id = edge.get("targetId")
    allowed = []
    points = route.get("points", [])
    if points:
        allowed.append(points[0])
        allowed.append(points[-1])

    for node_id, box in node_boxes.items():
        endpoint_allowed = allowed if node_id in (src_id, tgt_id) else []
        if route_overlaps_box(route, box, allowed_points=endpoint_allowed, clearance=EDGE_NODE_CLEARANCE):
            return f'edge "{edge.get("label", "?")}" overlaps node "{node_id}"'
        if boxes_overlap(route["labelBox"], expand_box(box, EDGE_NODE_CLEARANCE)):
            return f'edge label "{edge.get("label", "?")}" overlaps node "{node_id}"'

    for accepted in accepted_routes:
        accepted_edge = accepted.get("edge", {})
        if routes_overlap(route, accepted):
            return (
                f'edge "{edge.get("label", "?")}" overlaps edge '
                f'"{accepted_edge.get("label", "?")}"'
            )
        if boxes_overlap(route["labelBox"], accepted["labelBox"], EDGE_SEGMENT_CLEARANCE):
            return (
                f'edge label "{edge.get("label", "?")}" overlaps edge label '
                f'"{accepted_edge.get("label", "?")}"'
            )
        if route_label_overlaps_route(route["labelBox"], accepted):
            return (
                f'edge label "{edge.get("label", "?")}" overlaps edge '
                f'"{accepted_edge.get("label", "?")}"'
            )
        if route_label_overlaps_route(accepted["labelBox"], route):
            return (
                f'edge "{edge.get("label", "?")}" overlaps edge label '
                f'"{accepted_edge.get("label", "?")}"'
            )
    return None


def default_node_boxes(nodes_by_id, positions):
    return {
        node_id: node_box(node, positions[node_id])
        for node_id, node in nodes_by_id.items()
        if node_id in positions
    }


def diagram_bounds(node_boxes):
    if not node_boxes:
        return {"x": 0, "y": 0, "w": 0, "h": 0}
    min_x = min(box["x"] for box in node_boxes.values())
    min_y = min(box["y"] for box in node_boxes.values())
    max_x = max(box["x"] + box["w"] for box in node_boxes.values())
    max_y = max(box["y"] + box["h"] for box in node_boxes.values())
    return {"x": min_x, "y": min_y, "w": max_x - min_x, "h": max_y - min_y}


def candidate_edge_routes(edge, edge_index, nodes_by_id, positions, edges, node_boxes=None):
    src = nodes_by_id.get(edge.get("sourceId"))
    tgt = nodes_by_id.get(edge.get("targetId"))
    if not src or not tgt or src["id"] not in positions or tgt["id"] not in positions:
        return []
    node_boxes = node_boxes or default_node_boxes(nodes_by_id, positions)
    bounds = diagram_bounds(node_boxes)
    candidates = []

    base = edge_route(edge, edge_index, nodes_by_id, positions, edges)
    if base:
        candidates.append(base)

    src_box = node_box(src, positions[src["id"]])
    tgt_box = node_box(tgt, positions[tgt["id"]])

    if src["id"] == tgt["id"]:
        loop_offsets = [72, 120, 180, 260, 360]
        for side in ("right", "left", "top", "bottom"):
            for offset in loop_offsets:
                if side == "right":
                    x = src_box["x"] + src_box["w"] + offset
                    points = [
                        {"x": src_box["x"] + src_box["w"] + EDGE_END_PAD, "y": src_box["y"] + src_box["h"] * 0.35},
                        {"x": x, "y": src_box["y"] - offset * 0.35},
                        {"x": x, "y": src_box["y"] + src_box["h"] + offset * 0.35},
                        {"x": src_box["x"] + src_box["w"] + EDGE_END_PAD, "y": src_box["y"] + src_box["h"] * 0.65},
                    ]
                elif side == "left":
                    x = src_box["x"] - offset
                    points = [
                        {"x": src_box["x"] - EDGE_END_PAD, "y": src_box["y"] + src_box["h"] * 0.35},
                        {"x": x, "y": src_box["y"] - offset * 0.35},
                        {"x": x, "y": src_box["y"] + src_box["h"] + offset * 0.35},
                        {"x": src_box["x"] - EDGE_END_PAD, "y": src_box["y"] + src_box["h"] * 0.65},
                    ]
                elif side == "top":
                    y = src_box["y"] - offset
                    points = [
                        {"x": src_box["x"] + src_box["w"] * 0.35, "y": src_box["y"] - EDGE_END_PAD},
                        {"x": src_box["x"] - offset * 0.35, "y": y},
                        {"x": src_box["x"] + src_box["w"] + offset * 0.35, "y": y},
                        {"x": src_box["x"] + src_box["w"] * 0.65, "y": src_box["y"] - EDGE_END_PAD},
                    ]
                else:
                    y = src_box["y"] + src_box["h"] + offset
                    points = [
                        {"x": src_box["x"] + src_box["w"] * 0.35, "y": src_box["y"] + src_box["h"] + EDGE_END_PAD},
                        {"x": src_box["x"] - offset * 0.35, "y": y},
                        {"x": src_box["x"] + src_box["w"] + offset * 0.35, "y": y},
                        {"x": src_box["x"] + src_box["w"] * 0.65, "y": src_box["y"] + src_box["h"] + EDGE_END_PAD},
                    ]
                candidates.append(route_from_points(edge, src, tgt, points, longest_segment_midpoint(points)))
        return candidates

    side_pairs = [
        ("right", "left"), ("left", "right"), ("bottom", "top"), ("top", "bottom"),
        ("right", "right"), ("left", "left"), ("top", "top"), ("bottom", "bottom"),
    ]
    shifts = [0, 60, -60, 120, -120, 220, -220, 360, -360]
    for src_side, tgt_side in side_pairs:
        start = side_anchor(src, positions[src["id"]], src_side)
        end = side_anchor(tgt, positions[tgt["id"]], tgt_side)
        for shift in shifts:
            if src_side in ("left", "right") or tgt_side in ("left", "right"):
                mid_x = (start["x"] + end["x"]) / 2 + shift
                points = [start, {"x": mid_x, "y": start["y"]}, {"x": mid_x, "y": end["y"]}, end]
            else:
                mid_y = (start["y"] + end["y"]) / 2 + shift
                points = [start, {"x": start["x"], "y": mid_y}, {"x": end["x"], "y": mid_y}, end]
            candidates.append(route_from_points(edge, src, tgt, points, longest_segment_midpoint(points)))

    lanes = []
    for index in range(8):
        lanes.extend([
            ("top", bounds["y"] - 120 - index * 92),
            ("bottom", bounds["y"] + bounds["h"] + 120 + index * 92),
            ("left", bounds["x"] - 120 - index * 140),
            ("right", bounds["x"] + bounds["w"] + 120 + index * 140),
        ])
    for side, lane in lanes:
        if side in ("top", "bottom"):
            start = side_anchor(src, positions[src["id"]], "top" if side == "top" else "bottom")
            end = side_anchor(tgt, positions[tgt["id"]], "top" if side == "top" else "bottom")
            points = [start, {"x": start["x"], "y": lane}, {"x": end["x"], "y": lane}, end]
        else:
            start = side_anchor(src, positions[src["id"]], "left" if side == "left" else "right")
            end = side_anchor(tgt, positions[tgt["id"]], "left" if side == "left" else "right")
            points = [start, {"x": lane, "y": start["y"]}, {"x": lane, "y": end["y"]}, end]
        candidates.append(route_from_points(edge, src, tgt, points, longest_segment_midpoint(points)))

    for index in range(8):
        left_lane = bounds["x"] - 160 - index * 150
        right_lane = bounds["x"] + bounds["w"] + 160 + index * 150
        top_lane = bounds["y"] - 160 - index * 100
        bottom_lane = bounds["y"] + bounds["h"] + 160 + index * 100
        for x_side, x_lane in (("left", left_lane), ("right", right_lane)):
            for y_side, y_lane in (("top", top_lane), ("bottom", bottom_lane)):
                start = side_anchor(src, positions[src["id"]], x_side)
                end = side_anchor(tgt, positions[tgt["id"]], y_side)
                points = [
                    start,
                    {"x": x_lane, "y": start["y"]},
                    {"x": x_lane, "y": y_lane},
                    {"x": end["x"], "y": y_lane},
                    end,
                ]
                candidates.append(route_from_points(edge, src, tgt, points, longest_segment_midpoint(points)))

    return candidates


def select_non_overlapping_routes(edges, nodes_by_id, positions):
    node_boxes = default_node_boxes(nodes_by_id, positions)
    edges = edges or []
    candidate_sets = []
    for index, edge in enumerate(edges):
        candidates = candidate_edge_routes(edge, index, nodes_by_id, positions, edges, node_boxes)
        last_conflict = "no route candidates"
        viable = []
        for candidate in candidates:
            conflict = describe_route_conflict(candidate, node_boxes=node_boxes, accepted_routes=[])
            if conflict is None:
                viable.append(candidate)
            last_conflict = conflict or last_conflict
        if not viable:
            return None, f'Could not route edge "{edge.get("label", index)}" without overlap: {last_conflict}.'
        candidate_sets.append((edge, viable))

    attempts = 0
    max_attempts = 75000
    last_error = None

    def search(index, accepted):
        nonlocal attempts, last_error
        if index >= len(candidate_sets):
            return accepted
        edge, candidates = candidate_sets[index]
        for candidate in candidates:
            attempts += 1
            if attempts > max_attempts:
                last_error = "route search exceeded deterministic attempt limit"
                return None
            conflict = describe_route_conflict(candidate, node_boxes=node_boxes, accepted_routes=accepted)
            if conflict is not None:
                last_error = conflict
                continue
            result = search(index + 1, accepted + [candidate])
            if result is not None:
                return result
        if last_error is None:
            last_error = f'no compatible route candidates for edge "{edge.get("label", index)}"'
        return None

    result = search(0, [])
    if result is not None:
        return result, None
    failing_edge = edges[min(len(edges) - 1, len(candidate_sets) - 1)].get("label", len(candidate_sets) - 1) if edges else "?"
    if last_error:
        return None, f'Could not route edge "{failing_edge}" without overlap: {last_error}.'
    return None, "Could not route edges without overlap."


def boxes_overlap(a, b, gap=0):
    if not a or not b:
        return False
    return not (
        a["x"] + a["w"] + gap <= b["x"]
        or b["x"] + b["w"] + gap <= a["x"]
        or a["y"] + a["h"] + gap <= b["y"]
        or b["y"] + b["h"] + gap <= a["y"]
    )


def expand_box(box, pad):
    return {"x": box["x"] - pad, "y": box["y"] - pad, "w": box["w"] + pad * 2, "h": box["h"] + pad * 2}


def point_in_box(point, box):
    return bool(box and box["x"] <= point["x"] <= box["x"] + box["w"] and box["y"] <= point["y"] <= box["y"] + box["h"])


def read_json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
