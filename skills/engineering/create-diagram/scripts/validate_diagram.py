"""Validate generated diagram HTML.

Usage:
    python validate_diagram.py <path-to-diagram.html>
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from _diagram_utils import (
    CANONICAL_TYPES,
    DEFAULT_STORAGE_KEY,
    VALID_CLUSTER_LAYOUTS,
    VALID_CONFIDENCE,
    VALID_FIDELITY,
    all_nodes_have_positions,
    boxes_overlap,
    cluster_box,
    compute_layout,
    edge_route,
    evidence_quality,
    expand_box,
    extract_agent_metadata,
    extract_diagram_data,
    extract_raw_js_block,
    node_box,
    nodes_with_partial_positions,
    point_in_box,
    replace_js_assignment,
    resolve_type,
)

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "html-diagram-template.html"
INLINE_STYLE_RE = re.compile(
    r'<style\s+id="create-diagram-style"\s+data-inline-asset="css/style.css">.*?</style>',
    re.DOTALL,
)
INLINE_ROUGHJS_RE = re.compile(
    r'<script\s+id="create-diagram-roughjs"\s+data-inline-asset="roughjs.js">.*?</script>',
    re.DOTALL,
)
STYLE_LINK = '<link rel="stylesheet" href="css/style.css">'
ROUGHJS_SCRIPT = '<script src="roughjs.js"></script>'


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


def check_dangerous_js(raw_block):
    found = []
    for i, line in enumerate(raw_block.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if "`" in stripped:
            found.append((i, "template literal backtick string"))
        if "${" in stripped:
            found.append((i, "template interpolation ${}"))
    return found


def strip_data_sections(text):
    result = replace_js_assignment(text, "DIAGRAM_DATA", "const DIAGRAM_DATA = {};")
    result = INLINE_STYLE_RE.sub(STYLE_LINK, result)
    result = INLINE_ROUGHJS_RE.sub(ROUGHJS_SCRIPT, result)
    return re.sub(
        r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>',
        '<script type="application/json" id="agent-metadata">{}</script>',
        result,
        flags=re.DOTALL,
    )


def compute_template_hash(template_path):
    if not template_path.exists():
        return None
    clean = strip_data_sections(template_path.read_text(encoding="utf-8"))
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def check_template_integrity(output_path):
    template_hash = compute_template_hash(TEMPLATE_PATH)
    if template_hash is None:
        return [f"Template file not found at {TEMPLATE_PATH}"]
    output_text = output_path.read_text(encoding="utf-8")
    output_hash = hashlib.sha256(strip_data_sections(output_text).encode("utf-8")).hexdigest()
    if output_hash != template_hash:
        return [
            "Generated HTML has drifted from the canonical template outside DIAGRAM_DATA "
            "and #agent-metadata. Rebuild from assets/html-diagram-template.html."
        ]
    return []


def check_structural_completeness(text):
    issues = []
    if "</html>" not in text:
        issues.append("File is missing closing </html> tag; document may be truncated.")
    if "</body>" not in text:
        issues.append("File is missing closing </body> tag; document may be truncated.")
    if "init();" not in text or "</script>" not in text:
        issues.append("Missing init(); call or closing </script>; module script may be truncated.")
    return issues


def check_embedded_assets(text):
    issues = []
    style_match = INLINE_STYLE_RE.search(text)
    roughjs_match = INLINE_ROUGHJS_RE.search(text)
    if not style_match:
        issues.append(
            "Generated HTML is missing the embedded stylesheet. Rebuild with scripts/build_diagram.py."
        )
    elif not style_match.group(0).split(">", 1)[1].rsplit("</style>", 1)[0].strip():
        issues.append(
            "Generated HTML has an empty embedded stylesheet. Rebuild with scripts/build_diagram.py."
        )
    if not roughjs_match:
        issues.append(
            "Generated HTML is missing the embedded RoughJS runtime. Rebuild with scripts/build_diagram.py."
        )
    elif "window.roughjs" not in roughjs_match.group(0).split(">", 1)[1].rsplit("</script>", 1)[0]:
        issues.append(
            "Generated HTML has an invalid embedded RoughJS runtime. Rebuild with scripts/build_diagram.py."
        )
    if STYLE_LINK in text or ROUGHJS_SCRIPT in text:
        issues.append(
            "Generated HTML still references external local assets. Rebuild with scripts/build_diagram.py "
            "so the artifact is portable."
        )
    return issues


def validate_geometry(data, emit_error):
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    clusters = data.get("clusters") or []
    if not nodes:
        return
    positions = compute_layout(data)
    nodes_by_id = {n.get("id"): n for n in nodes if n.get("id")}
    cluster_by_node = {}
    for cluster in clusters:
        cid = cluster.get("id") or cluster.get("label") or "?"
        for node_id in cluster.get("nodeIds") or []:
            cluster_by_node[node_id] = cid

    cluster_boxes = {}
    for cluster in clusters:
        cid = cluster.get("id") or cluster.get("label") or "?"
        cbox = cluster_box(cluster, nodes_by_id, positions)
        if cbox:
            cluster_boxes[cid] = cbox

    routes = []
    for index, edge in enumerate(edges):
        route = edge_route(edge, index, nodes_by_id, positions, edges)
        if route:
            routes.append(route)

    for route in routes:
        edge = route["edge"]
        source_id = edge.get("sourceId")
        target_id = edge.get("targetId")
        source_cluster = cluster_by_node.get(source_id)
        target_cluster = cluster_by_node.get(target_id)

        for node_id, node in nodes_by_id.items():
            if node_id in (source_id, target_id) or node_id not in positions:
                continue
            nbox = expand_box(node_box(node, positions[node_id]), 8)
            if any(point_in_box(sample, nbox) for sample in route["samples"][1:-1]):
                emit_error(
                    f'Edge "{edge.get("label", "?")}" ({source_id} -> {target_id}) '
                    f'passes through node "{node_id}".'
                )
            if boxes_overlap(route["labelBox"], expand_box(nbox, 12)):
                emit_error(
                    f'Edge label "{edge.get("label", "?")}" ({source_id} -> {target_id}) '
                    f'overlaps node "{node.get("label", node_id)}".'
                )

        for cid, cbox in cluster_boxes.items():
            if cid in (source_cluster, target_cluster):
                continue
            if any(point_in_box(sample, expand_box(cbox, 4)) for sample in route["samples"]):
                emit_error(
                    f'Edge "{edge.get("label", "?")}" ({source_id} -> {target_id}) '
                    f'passes through cluster "{cid}".'
                )
            if boxes_overlap(route["labelBox"], expand_box(cbox, 8)):
                emit_error(
                    f'Edge label "{edge.get("label", "?")}" ({source_id} -> {target_id}) '
                    f'overlaps cluster "{cid}".'
                )

    for index, route in enumerate(routes):
        for other in routes[index + 1:]:
            if boxes_overlap(route["labelBox"], other["labelBox"], 8):
                emit_error(
                    f'Edge label "{route["edge"].get("label", "?")}" overlaps edge label '
                    f'"{other["edge"].get("label", "?")}".'
                )


def validate(data, metadata):
    errors = 0
    warnings = 0
    node_ids = set()
    node_labels = {}
    node_types_map = {}

    def emit_error(msg):
        nonlocal errors
        errors += 1
        fail(msg)

    def emit_warning(msg):
        nonlocal warnings
        warnings += 1
        warn(msg)

    if not isinstance(data, dict):
        emit_error("DIAGRAM_DATA is not a valid JSON object.")
        return errors, warnings

    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        emit_error("DIAGRAM_DATA.title is missing or empty.")

    if data.get("storageKey") == DEFAULT_STORAGE_KEY:
        emit_warning(f'storageKey is "{DEFAULT_STORAGE_KEY}". Set a unique key or omit it.')

    fidelity = data.get("fidelity")
    if fidelity and fidelity not in VALID_FIDELITY:
        emit_error(f'Unknown fidelity "{fidelity}". Valid values: {", ".join(sorted(VALID_FIDELITY))}.')

    takeaways = data.get("takeaways")
    if takeaways and len(takeaways) > 3:
        emit_warning("takeaways has more than 3 items; brief panel may be hard to scan.")

    nodes = data.get("nodes")
    incident_edge_count = {}
    if not isinstance(nodes, list):
        emit_error("DIAGRAM_DATA.nodes is missing or not an array.")
        nodes = []
    else:
        if not nodes:
            emit_error("DIAGRAM_DATA.nodes is empty.")
        partial = nodes_with_partial_positions(nodes)
        for node_id in partial:
            emit_error(f'Node "{node_id}" has only one manual coordinate. Provide both x and y or neither.')
        positioned_count = sum(1 for n in nodes if "x" in n and "y" in n and n.get("x") is not None and n.get("y") is not None)
        if positioned_count and not all_nodes_have_positions(nodes):
            emit_error("Manual node positions must be all-or-none; omit all x/y values to use auto-layout.")

        seen = set()
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                emit_error(f"nodes[{i}] is not an object.")
                continue
            node_id = node.get("id")
            if not node_id or not isinstance(node_id, str):
                emit_error(f"nodes[{i}] is missing a valid 'id' (non-empty string).")
                continue
            if node_id in seen:
                emit_error(f'Duplicate node id "{node_id}".')
            seen.add(node_id)
            node_ids.add(node_id)
            node_labels[node_id] = node.get("label", "")
            node_types_map[node_id] = resolve_type(node.get("type", ""))
            incident_edge_count[node_id] = 0

            label = node.get("label")
            if not label or not isinstance(label, str):
                emit_error(f'Node "{node_id}" is missing a valid "label" (non-empty string).')

            node_type = node.get("type")
            if not node_type or not isinstance(node_type, str):
                emit_error(f'Node "{node_id}" is missing a valid "type".')
            elif resolve_type(node_type) not in CANONICAL_TYPES:
                emit_error(f'Node "{node_id}" has unknown type "{node_type}".')

            desc = node.get("description")
            if desc is not None:
                if not isinstance(desc, str):
                    emit_error(f'Node "{node_id}" description must be a string.')
                elif len(desc) < 15 or len(desc) > 96:
                    emit_warning(f'Node "{node_id}" description is {len(desc)} chars (recommended 15-96).')

    edges = data.get("edges")
    if not isinstance(edges, list):
        emit_error("DIAGRAM_DATA.edges is missing or not an array.")
        edges = []
    else:
        seen_edges = set()
        for i, edge in enumerate(edges):
            if not isinstance(edge, dict):
                emit_error(f"edges[{i}] is not an object.")
                continue
            src = edge.get("sourceId")
            tgt = edge.get("targetId")
            label = edge.get("label")

            if not src or not isinstance(src, str) or src not in node_ids:
                emit_error(f'Edge "{label or i}" has dangling or missing sourceId "{src}".')
            else:
                incident_edge_count[src] = incident_edge_count.get(src, 0) + 1
            if not tgt or not isinstance(tgt, str) or tgt not in node_ids:
                emit_error(f'Edge "{label or i}" has dangling or missing targetId "{tgt}".')
            else:
                incident_edge_count[tgt] = incident_edge_count.get(tgt, 0) + 1
            if not label or not isinstance(label, str) or not label.strip():
                emit_error(f'Edge at index {i} is missing a valid "label" (non-empty string).')

            evidence = edge.get("evidence")
            if not evidence or not isinstance(evidence, str) or not evidence.strip():
                emit_error(f'Edge "{label or i}" is missing "evidence".')
            else:
                eq = evidence_quality(evidence)
                if eq:
                    emit_warning(f'Edge "{label or i}" evidence "{evidence}" has {eq}.')

            confidence = edge.get("confidence")
            if not confidence or confidence not in VALID_CONFIDENCE:
                emit_error(f'Edge "{label or i}" has invalid confidence "{confidence}".')

            edge_key = (src, tgt, label)
            if edge_key in seen_edges:
                emit_warning(f'Duplicate edge: {src} -> {tgt} label="{label}".')
            seen_edges.add(edge_key)

    clusters = data.get("clusters")
    cluster_membership = {}
    if isinstance(clusters, list):
        for cluster in clusters:
            if not isinstance(cluster, dict):
                emit_error("clusters has a non-object entry.")
                continue
            cid = cluster.get("id") or cluster.get("label")
            if not cid:
                emit_warning("Cluster has no id or label.")
            layout = cluster.get("layout")
            if layout is not None and layout not in VALID_CLUSTER_LAYOUTS:
                emit_error(f'Cluster "{cid or "?"}" has invalid layout "{layout}".')
            for node_id in cluster.get("nodeIds") or []:
                cluster_membership.setdefault(node_id, []).append(cid or "?")
                if node_id not in node_ids:
                    emit_error(f'Cluster "{cid or "?"}" references missing node "{node_id}".')

    for node_id, memberships in cluster_membership.items():
        if len(memberships) > 1:
            emit_error(f'Node "{node_id}" belongs to {len(memberships)} clusters: {", ".join(memberships)}.')

    for node_id in node_ids:
        if incident_edge_count.get(node_id, 0) == 0 and node_id not in cluster_membership:
            emit_warning(f'Node "{node_id}" has no incident edges and belongs to no cluster; it may be orphaned.')

    # Visual overlap checks are intentionally not blocking here. The shared
    # geometry helpers are used by the exporter, while the HTML renderer keeps
    # final visual layout interactive and adjustable by the user.

    walkthrough = data.get("walkthrough")
    if isinstance(walkthrough, list):
        step_ids = set()
        for i, step in enumerate(walkthrough):
            if not isinstance(step, dict):
                emit_error(f"walkthrough[{i}] is not an object.")
                continue
            step_id = step.get("id")
            if not step_id or not isinstance(step_id, str):
                emit_error(f"walkthrough[{i}] is missing a valid 'id' (non-empty string).")
            elif step_id in step_ids:
                emit_error(f'Duplicate walkthrough step id "{step_id}".')
            step_ids.add(step_id)

            title = step.get("title")
            if not title or not isinstance(title, str) or not title.strip():
                emit_error(f'Walkthrough step "{step_id or i}" is missing a valid "title".')
            step_nodes = step.get("nodeIds")
            if not isinstance(step_nodes, list) or not step_nodes:
                emit_error(f'Walkthrough step "{step_id or i}" has no nodeIds.')
            else:
                for node_id in step_nodes:
                    if node_id not in node_ids:
                        emit_error(f'Walkthrough step "{step_id or i}" references missing node "{node_id}".')
                if len(step_nodes) >= 2:
                    step_set = set(step_nodes)
                    visible_edges = sum(
                        1 for edge in edges
                        if edge.get("sourceId") in step_set and edge.get("targetId") in step_set
                    )
                    if visible_edges == 0:
                        emit_warning(f'Walkthrough step "{step_id or i}" has no edges connecting its nodes.')

    if not isinstance(metadata, dict) or not metadata:
        emit_error("#agent-metadata is missing or invalid.")
        return errors, warnings

    for field in ("audience", "purpose", "fidelity"):
        data_value = data.get(field)
        meta_value = metadata.get(field)
        if data_value and meta_value and data_value != meta_value:
            emit_error(f"#agent-metadata.{field} does not match DIAGRAM_DATA.{field}.")

    meta_entities = metadata.get("entities") or []
    meta_entity_ids = set()
    for i, entity in enumerate(meta_entities):
        entity_id = entity.get("id")
        if not entity_id:
            emit_error(f"metadata entities[{i}] is missing an 'id'.")
            continue
        meta_entity_ids.add(entity_id)
        if entity_id not in node_ids:
            emit_error(f"metadata entity '{entity_id}' has no matching DIAGRAM_DATA node.")
            continue
        if entity.get("name") and entity.get("name") != node_labels.get(entity_id):
            emit_warning(f'metadata entity "{entity_id}" name differs from DIAGRAM_DATA node label.')
        entity_type = resolve_type(entity.get("type", ""))
        if entity_type and entity_type != node_types_map.get(entity_id):
            emit_error(f'metadata entity "{entity_id}" type differs from DIAGRAM_DATA node type.')

    for node_id in node_ids:
        if node_id not in meta_entity_ids:
            emit_error(f"DIAGRAM_DATA node '{node_id}' is missing from #agent-metadata entities.")

    for i, rel in enumerate(metadata.get("relationships") or []):
        src = rel.get("sourceId")
        tgt = rel.get("targetId")
        label = rel.get("label") or f"relationship[{i}]"
        if not rel.get("label"):
            emit_error(f"metadata relationships[{i}] is missing 'label'.")
        if src and src not in node_ids:
            emit_error(f"metadata relationship '{label}' has dangling source '{src}'.")
        if tgt and tgt not in node_ids:
            emit_error(f"metadata relationship '{label}' has dangling target '{tgt}'.")
        confidence = rel.get("confidence")
        if confidence and confidence not in VALID_CONFIDENCE:
            emit_error(f"metadata relationship '{label}' has invalid confidence '{confidence}'.")
        evidence = rel.get("evidence")
        if not evidence:
            emit_error(f"metadata relationship '{label}' is missing 'evidence'.")
        else:
            eq = evidence_quality(evidence)
            if eq:
                emit_warning(f'metadata relationship "{label}" evidence "{evidence}" has {eq}.')

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_diagram.py <path-to-diagram.html>", file=sys.stderr)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    if not html_path.exists():
        fail(f"File not found: {html_path}")
        sys.exit(1)
    if TEMPLATE_PATH.exists() and html_path.resolve() == TEMPLATE_PATH.resolve():
        fail(f"Output path is the template file itself ({TEMPLATE_PATH}). Save to a different file.")
        sys.exit(1)

    text = html_path.read_text(encoding="utf-8")
    for issue in check_structural_completeness(text):
        fail(issue)
        sys.exit(1)
    for issue in check_embedded_assets(text):
        fail(issue)
        sys.exit(1)

    try:
        metadata = extract_agent_metadata(text, required=True)
    except ValueError as exc:
        fail(str(exc))
        sys.exit(1)

    for issue in check_template_integrity(html_path):
        fail(issue)
        sys.exit(1)

    raw_block = extract_raw_js_block(text, "DIAGRAM_DATA")
    if raw_block is None:
        fail("Could not find 'const DIAGRAM_DATA =' in file.")
        sys.exit(1)

    dangerous = check_dangerous_js(raw_block)
    if dangerous:
        for line, desc in dangerous:
            fail(f"DIAGRAM_DATA line {line}: {desc}. The parser cannot handle this syntax.")
        sys.exit(1)

    try:
        data = extract_diagram_data(text)
    except ValueError as exc:
        fail(str(exc))
        sys.exit(1)

    errors, warnings = validate(data, metadata)
    if errors:
        print(f"\n{errors} error(s), {warnings} warning(s) found.", file=sys.stderr)
        sys.exit(1)
    print(f"Valid - 0 errors, {warnings} warning(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
