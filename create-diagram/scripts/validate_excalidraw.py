"""Validate generated .excalidraw files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _diagram_utils import (
    describe_route_conflict,
    route_from_points,
)


VALID_ELEMENT_TYPES = frozenset({
    "rectangle", "diamond", "ellipse", "arrow", "text", "line",
    "freedraw", "image", "embeddable", "iframe",
})


def element_box(element):
    return {
        "x": float(element.get("x", 0)),
        "y": float(element.get("y", 0)),
        "w": float(element.get("width", 0)),
        "h": float(element.get("height", 0)),
    }


def absolute_arrow_points(element):
    base_x = float(element.get("x", 0))
    base_y = float(element.get("y", 0))
    points = element.get("points") or []
    return [{"x": base_x + float(point[0]), "y": base_y + float(point[1])} for point in points]


def edge_label_for_arrow(arrow, by_id):
    bound = arrow.get("boundElements") or []
    for item in bound:
        if not isinstance(item, dict):
            continue
        candidate = by_id.get(item.get("id"))
        if candidate and candidate.get("type") == "text":
            return candidate
    return by_id.get(f"{arrow.get('id')}-label")


def validate_edge_overlaps(elements, emit_error):
    by_id = {element.get("id"): element for element in elements if isinstance(element, dict) and element.get("id")}
    arrows = [element for element in elements if isinstance(element, dict) and element.get("type") == "arrow"]
    edge_label_ids = set()
    for arrow in arrows:
        label = edge_label_for_arrow(arrow, by_id)
        if isinstance(label, dict) and label.get("id"):
            edge_label_ids.add(label["id"])

    node_boxes = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        element_id = element.get("id", "")
        element_type = element.get("type")
        if element_type == "arrow":
            continue
        if element_id.startswith("cluster-"):
            continue
        if element_type == "text":
            if element_id in edge_label_ids:
                continue
            container = by_id.get(element.get("containerId"))
            if not container or container.get("type") == "arrow" or str(container.get("id", "")).startswith("cluster-"):
                continue
        node_boxes[element_id] = element_box(element)

    accepted_routes = []
    for arrow in arrows:
        points = absolute_arrow_points(arrow)
        if len(points) < 2:
            continue
        start_binding = arrow.get("startBinding") or {}
        end_binding = arrow.get("endBinding") or {}
        source_id = start_binding.get("elementId")
        target_id = end_binding.get("elementId")
        label_element = edge_label_for_arrow(arrow, by_id)
        edge = {
            "sourceId": source_id,
            "targetId": target_id,
            "label": label_element.get("text") if isinstance(label_element, dict) else arrow.get("id", "?"),
        }
        route = route_from_points(edge, {"id": source_id}, {"id": target_id}, points)
        if isinstance(label_element, dict):
            route["labelBox"] = element_box(label_element)
        conflict = describe_route_conflict(route, node_boxes=node_boxes, accepted_routes=accepted_routes)
        if conflict:
            emit_error(f"Excalidraw edge overlap: {conflict}.")
        accepted_routes.append(route)


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg):
    print(f"WARNING: {msg}", file=sys.stderr)


def validate(doc):
    errors = 0
    warnings = 0

    def emit_error(msg):
        nonlocal errors
        errors += 1
        fail(msg)

    def emit_warning(msg):
        nonlocal warnings
        warnings += 1
        warn(msg)

    if not isinstance(doc, dict):
        emit_error("Document root is not a JSON object.")
        return errors, warnings

    if doc.get("type") != "excalidraw":
        emit_error(f'Document type is "{doc.get("type")}", expected "excalidraw".')

    version = doc.get("version")
    if not isinstance(version, (int, float)):
        emit_error(f"Document version is missing or not a number (got {type(version).__name__}).")
    elif version < 2:
        emit_error(f"Document version is {version}, expected >= 2.")

    elements = doc.get("elements")
    if not isinstance(elements, list):
        emit_error("Document 'elements' is missing or not an array.")
        elements = []
    elif not elements:
        emit_warning("Document 'elements' is empty; the diagram will be blank.")

    element_ids = set()
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            emit_error(f"elements[{index}] is not an object.")
            continue
        element_id = element.get("id")
        if not element_id or not isinstance(element_id, str):
            emit_error(f"elements[{index}] is missing a valid 'id' (non-empty string).")
            continue
        if element_id in element_ids:
            emit_error(f'Duplicate element id "{element_id}".')
        element_ids.add(element_id)

    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            continue
        element_id = element.get("id") or f"elements[{index}]"
        element_type = element.get("type")
        for field in ("type", "x", "y", "width", "height"):
            if field not in element:
                emit_error(f'Element "{element_id}" is missing "{field}".')
        if element_type and element_type not in VALID_ELEMENT_TYPES:
            emit_error(f'Element "{element_id}" has unknown type "{element_type}".')
        for field in ("x", "y", "width", "height"):
            if field in element and not isinstance(element.get(field), (int, float)):
                emit_error(f'Element "{element_id}" field "{field}" is not numeric.')

        if element_type == "arrow":
            points = element.get("points")
            if not isinstance(points, list) or len(points) < 2:
                emit_error(f'Arrow element "{element_id}" has invalid "points" (expected array of >=2 points).')
            else:
                for point_index, point in enumerate(points):
                    if (
                        not isinstance(point, list)
                        or len(point) != 2
                        or not all(isinstance(value, (int, float)) for value in point)
                    ):
                        emit_error(f'Arrow element "{element_id}" point {point_index} is invalid.')
            for binding_name in ("startBinding", "endBinding"):
                binding = element.get(binding_name)
                if isinstance(binding, dict):
                    bound_id = binding.get("elementId")
                    if bound_id and bound_id not in element_ids:
                        emit_error(f'Arrow "{element_id}" {binding_name} references unknown element "{bound_id}".')

        if element_type == "text":
            container_id = element.get("containerId")
            if container_id and container_id not in element_ids:
                emit_error(f'Text element "{element_id}" containerId references unknown element "{container_id}".')
            if "text" not in element:
                emit_error(f'Text element "{element_id}" is missing "text".')

        bound = element.get("boundElements")
        if isinstance(bound, list):
            for bound_element in bound:
                if isinstance(bound_element, dict):
                    bound_id = bound_element.get("id")
                    if bound_id and bound_id not in element_ids:
                        emit_error(f'Element "{element_id}" boundElements references unknown element "{bound_id}".')

        if element.get("isDeleted") is True:
            emit_warning(f'Element "{element_id}" has isDeleted=true; it will not render.')

    app_state = doc.get("appState")
    if app_state is None:
        emit_warning('Document is missing "appState".')
    elif not isinstance(app_state, dict):
        emit_error('Document "appState" is not an object.')

    validate_edge_overlaps(elements, emit_error)

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_excalidraw.py <path-to-diagram.excalidraw>", file=sys.stderr)
        sys.exit(1)

    exc_path = Path(sys.argv[1])
    if not exc_path.exists():
        fail(f"File not found: {exc_path}")
        sys.exit(1)
    if exc_path.suffix.lower() not in (".excalidraw", ".json"):
        warn(f"File extension is '{exc_path.suffix}', expected '.excalidraw' or '.json'.")

    try:
        doc = json.loads(exc_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Could not parse JSON: {exc}")
        sys.exit(1)

    errors, warnings = validate(doc)
    if errors:
        print(f"\n{errors} error(s), {warnings} warning(s) found.", file=sys.stderr)
        sys.exit(1)
    print(f"Valid - 0 errors, {warnings} warning(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
