from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "test" / "fixtures"
TEMPLATE = ROOT / "assets" / "html-excalidraw-template.html"
SKILL_DOC = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"
sys.path.insert(0, str(SCRIPTS))

import build_diagram  # noqa: E402
import generate_excalidraw  # noqa: E402
import validate_diagram  # noqa: E402
import validate_excalidraw  # noqa: E402
from _diagram_utils import extract_diagram_data  # noqa: E402


def load_complex_payload():
    return json.loads((FIXTURES / "complex.json").read_text(encoding="utf-8"))


def minimal_payload():
    return {
        "diagram": {
            "title": "Minimal Diagram",
            "audience": "Engineers",
            "purpose": "Validate a tiny happy path.",
            "fidelity": "narrative-architecture",
            "nodes": [
                {
                    "id": "a",
                    "label": "Source",
                    "type": "service",
                    "description": "Starts the validated diagram flow."
                },
                {
                    "id": "b",
                    "label": "Target",
                    "type": "database",
                    "description": "Receives the validated diagram flow."
                }
            ],
            "edges": [
                {
                    "sourceId": "a",
                    "targetId": "b",
                    "label": "writes",
                    "evidence": "user-stated",
                    "confidence": "stated"
                }
            ],
            "clusters": [
                {
                    "id": "main",
                    "label": "Main",
                    "nodeIds": ["a", "b"]
                }
            ]
        },
        "metadata": {
            "audience": "Engineers",
            "purpose": "Validate a tiny happy path.",
            "fidelity": "narrative-architecture",
            "entities": [
                {
                    "id": "a",
                    "name": "Source",
                    "type": "service",
                    "description": "Starts the validated diagram flow.",
                    "evidence": "user-stated"
                },
                {
                    "id": "b",
                    "name": "Target",
                    "type": "database",
                    "description": "Receives the validated diagram flow.",
                    "evidence": "user-stated"
                }
            ],
            "relationships": [
                {
                    "sourceId": "a",
                    "targetId": "b",
                    "label": "writes",
                    "direction": "Source -> Target",
                    "confidence": "stated",
                    "evidence": "user-stated"
                }
            ],
            "assumptions": [],
            "omissions": [],
            "openQuestions": [],
            "agentInstructions": [
                "Keep ids stable."
            ]
        }
    }


def excalidraw_doc(elements):
    return {
        "type": "excalidraw",
        "version": 2,
        "elements": elements,
        "appState": {},
    }


def rect(element_id, x, y, width=100, height=80):
    return {
        "id": element_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def text(element_id, x, y, width, height, value, container_id=None):
    item = {
        "id": element_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "text": value,
    }
    if container_id:
        item["containerId"] = container_id
    return item


def arrow(element_id, points, source_id, target_id, label_id=None):
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_x = max(point[0] for point in points)
    max_y = max(point[1] for point in points)
    item = {
        "id": element_id,
        "type": "arrow",
        "x": min_x,
        "y": min_y,
        "width": max(max_x - min_x, 1),
        "height": max(max_y - min_y, 1),
        "points": [[point[0] - min_x, point[1] - min_y] for point in points],
        "startBinding": {"elementId": source_id},
        "endBinding": {"elementId": target_id},
    }
    if label_id:
        item["boundElements"] = [{"type": "text", "id": label_id}]
    return item


def write_payload(payload, tmp, name="diagram"):
    payload_path = Path(tmp) / f"{name}.json"
    html_path = Path(tmp) / f"{name}.html"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    build_diagram.build_diagram(payload_path, html_path, overwrite=True)
    return html_path


class DiagramToolTests(unittest.TestCase):
    def validate_payload(self, payload):
        return validate_diagram.validate(payload["diagram"], payload["metadata"])

    def test_minimal_payload_validates(self):
        errors, warnings = self.validate_payload(minimal_payload())
        self.assertEqual(errors, 0)
        self.assertEqual(warnings, 0)

    def test_complex_fixture_validates_and_preserves_literal_braces(self):
        payload = load_complex_payload()
        errors, warnings = self.validate_payload(payload)
        self.assertEqual(errors, 0)
        self.assertEqual(warnings, 0)

        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            html_path = Path(tmp) / "diagram.html"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            build_diagram.build_diagram(payload_path, html_path, overwrite=True)
            data = extract_diagram_data(html_path.read_text(encoding="utf-8"))
            self.assertEqual(data["nodes"][6]["label"], "Notes {JSON}")

    def test_html_template_uses_font_menu_instead_of_fit_button(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="font-menu-toggle"', text)
        self.assertIn('id="font-menu"', text)
        self.assertIn("localStorage.getItem('diagram-font')", text)
        self.assertIn("localStorage.setItem('diagram-font'", text)
        self.assertNotIn("zoom-readable", text)
        self.assertNotIn(">Fit</button>", text)

        match = re.search(r"const DIAGRAM_FONTS = \[(.*?)\];", text, re.S)
        self.assertIsNotNone(match)
        fonts = re.findall(r"name: '([^']+)'", match.group(1))
        self.assertEqual(len(fonts), 10)
        self.assertIn("Indie Flower", fonts)

    def test_builder_rejects_existing_output_without_overwrite(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            html_path = Path(tmp) / "diagram.html"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            html_path.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                build_diagram.build_diagram(payload_path, html_path, overwrite=False)

    def test_builder_refuses_missing_directory_without_create_dirs(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            html_path = Path(tmp) / "missing" / "diagram.html"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                build_diagram.build_diagram(payload_path, html_path)

            self.assertFalse(html_path.exists())

    def test_builder_create_dirs_and_atomic_write(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            html_path = Path(tmp) / "missing" / "diagram.html"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            build_diagram.build_diagram(payload_path, html_path, create_dirs=True)

            self.assertTrue(html_path.exists())
            self.assertFalse((html_path.parent / ".diagram.html.tmp").exists())
            self.assertIn("const DIAGRAM_DATA =", html_path.read_text(encoding="utf-8"))

    def test_excalidraw_export_validates(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            self.assertTrue(generate_excalidraw.generate(html_path))
            exc_path = html_path.with_suffix(".excalidraw")
            doc = json.loads(exc_path.read_text(encoding="utf-8"))
            errors, warnings = validate_excalidraw.validate(doc)
            self.assertEqual(errors, 0)
            self.assertEqual(warnings, 0)
            text_values = [el.get("text", "") for el in doc["elements"] if el.get("type") == "text"]
            self.assertTrue(any("Starts the validated diagram flow" in value for value in text_values))

    def test_excalidraw_generation_refuses_existing_output_without_overwrite(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            exc_path = html_path.with_suffix(".excalidraw")
            exc_path.write_text("existing", encoding="utf-8")

            self.assertFalse(generate_excalidraw.generate(html_path))
            self.assertEqual(exc_path.read_text(encoding="utf-8"), "existing")

            self.assertTrue(generate_excalidraw.generate(html_path, overwrite=True))
            self.assertEqual(json.loads(exc_path.read_text(encoding="utf-8"))["type"], "excalidraw")

    def test_excalidraw_generation_refuses_invalid_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "diagram.html"
            html_path.write_text("<html><body>broken</body></html>", encoding="utf-8")

            self.assertFalse(generate_excalidraw.generate(html_path))
            self.assertFalse(html_path.with_suffix(".excalidraw").exists())

    def test_complex_fixture_excalidraw_export_validates(self):
        payload = load_complex_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp, "complex")
            self.assertTrue(generate_excalidraw.generate(html_path))
            doc = json.loads(html_path.with_suffix(".excalidraw").read_text(encoding="utf-8"))
            errors, warnings = validate_excalidraw.validate(doc)
            self.assertEqual(errors, 0)
            self.assertEqual(warnings, 0)

    def test_excalidraw_generation_reroutes_around_between_node(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"].append({
            "id": "middle",
            "label": "Middle",
            "type": "process",
            "description": "Sits between source and target and forces a detour.",
            "x": 430,
            "y": 85,
        })
        payload["diagram"]["nodes"][0].update({"x": 0, "y": 100})
        payload["diagram"]["nodes"][1].update({"x": 900, "y": 100})
        payload["metadata"]["entities"].append({
            "id": "middle",
            "name": "Middle",
            "type": "process",
            "description": "Sits between source and target and forces a detour.",
            "evidence": "user-stated",
        })

        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            self.assertTrue(generate_excalidraw.generate(html_path))
            doc = json.loads(html_path.with_suffix(".excalidraw").read_text(encoding="utf-8"))
            errors, warnings = validate_excalidraw.validate(doc)
            self.assertEqual(errors, 0)
            self.assertEqual(warnings, 0)

    def test_excalidraw_validator_rejects_crossing_arrows(self):
        doc = excalidraw_doc([
            rect("a", 0, 0),
            rect("b", 300, 300),
            rect("c", 0, 300),
            rect("d", 300, 0),
            arrow("edge-1", [(100, 40), (300, 340)], "a", "b"),
            arrow("edge-2", [(100, 340), (300, 40)], "c", "d"),
        ])
        errors, _warnings = validate_excalidraw.validate(doc)
        self.assertGreater(errors, 0)

    def test_excalidraw_validator_rejects_arrow_through_node(self):
        doc = excalidraw_doc([
            rect("a", 0, 0),
            rect("b", 400, 0),
            rect("blocker", 190, -10, 100, 100),
            arrow("edge-1", [(100, 40), (400, 40)], "a", "b"),
        ])
        errors, _warnings = validate_excalidraw.validate(doc)
        self.assertGreater(errors, 0)

    def test_excalidraw_validator_rejects_edge_label_over_node(self):
        doc = excalidraw_doc([
            rect("a", 0, 0),
            rect("b", 400, 0),
            rect("blocker", 200, 110, 100, 90),
            arrow("edge-1", [(100, 40), (240, -90), (400, 40)], "a", "b", "edge-label"),
            text("edge-label", 210, 130, 90, 34, "overlaps"),
        ])
        errors, _warnings = validate_excalidraw.validate(doc)
        self.assertGreater(errors, 0)

    def test_excalidraw_validator_rejects_overlapping_edge_labels(self):
        doc = excalidraw_doc([
            rect("a", 0, 0),
            rect("b", 300, 0),
            rect("c", 0, 300),
            rect("d", 300, 300),
            arrow("edge-1", [(100, 40), (300, 40)], "a", "b", "edge-1-label"),
            text("edge-1-label", 160, 170, 90, 34, "same spot"),
            arrow("edge-2", [(100, 340), (300, 340)], "c", "d", "edge-2-label"),
            text("edge-2-label", 165, 175, 90, 34, "same spot"),
        ])
        errors, _warnings = validate_excalidraw.validate(doc)
        self.assertGreater(errors, 0)

    def test_excalidraw_self_loop_routes_outside_node(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"] = [payload["diagram"]["nodes"][0]]
        payload["diagram"]["edges"] = [{
            "sourceId": "a",
            "targetId": "a",
            "label": "retries",
            "evidence": "user-stated",
            "confidence": "stated",
        }]
        payload["diagram"]["clusters"][0]["nodeIds"] = ["a"]
        payload["metadata"]["entities"] = [payload["metadata"]["entities"][0]]
        payload["metadata"]["relationships"] = [{
            "sourceId": "a",
            "targetId": "a",
            "label": "retries",
            "direction": "Source -> Source",
            "confidence": "stated",
            "evidence": "user-stated",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            self.assertTrue(generate_excalidraw.generate(html_path))
            doc = json.loads(html_path.with_suffix(".excalidraw").read_text(encoding="utf-8"))
            errors, warnings = validate_excalidraw.validate(doc)
            self.assertEqual(errors, 0)
            self.assertEqual(warnings, 0)

    def test_excalidraw_generation_fails_before_writing_impossible_route(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"][0].update({"x": 100, "y": 100})
        payload["diagram"]["nodes"][1].update({"x": 520, "y": 100})
        payload["diagram"]["nodes"][0]["description"] = ""
        payload["diagram"]["nodes"][1]["description"] = ""
        payload["diagram"]["nodes"].append({
            "id": "blocker",
            "label": "Blocker " + ("wide " * 120),
            "type": "process",
            "description": "Covers every source and target anchor exit before routing can leave the node.",
            "x": -100,
            "y": 40,
        })
        payload["metadata"]["entities"].append({
            "id": "blocker",
            "name": "Blocker " + ("wide " * 120),
            "type": "process",
            "description": "Covers all possible source and target anchor exits.",
            "evidence": "user-stated",
        })

        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            exc_path = html_path.with_suffix(".excalidraw")
            self.assertFalse(generate_excalidraw.generate(html_path))
            self.assertFalse(exc_path.exists())

    def test_invalid_duplicate_ids(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"][1]["id"] = "a"
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_invalid_dangling_edge(self):
        payload = minimal_payload()
        payload["diagram"]["edges"][0]["targetId"] = "missing"
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_invalid_missing_evidence_and_confidence(self):
        payload = minimal_payload()
        edge = payload["diagram"]["edges"][0]
        edge.pop("evidence")
        edge.pop("confidence")
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_invalid_bad_metadata(self):
        payload = minimal_payload()
        payload["metadata"]["entities"][0]["id"] = "missing"
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_invalid_partial_manual_position(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"][0]["x"] = 10
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_invalid_mixed_manual_positions(self):
        payload = minimal_payload()
        payload["diagram"]["nodes"][0]["x"] = 10
        payload["diagram"]["nodes"][0]["y"] = 10
        errors, _warnings = self.validate_payload(payload)
        self.assertGreater(errors, 0)

    def test_cli_smoke_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "smoke.html"
            exc_path = html_path.with_suffix(".excalidraw")
            commands = [
                [sys.executable, str(SCRIPTS / "check_template_refs.py")],
                [
                    sys.executable,
                    str(SCRIPTS / "build_diagram.py"),
                    "--data",
                    str(FIXTURES / "complex.json"),
                    "--output",
                    str(html_path),
                    "--overwrite",
                ],
                [sys.executable, str(SCRIPTS / "validate_diagram.py"), str(html_path)],
                [sys.executable, str(SCRIPTS / "generate_excalidraw.py"), str(html_path)],
                [sys.executable, str(SCRIPTS / "validate_excalidraw.py"), str(exc_path)],
            ]
            for command in commands:
                with self.subTest(command=command):
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_docs_use_anchored_script_commands(self):
        docs = [SKILL_DOC.read_text(encoding="utf-8")]
        docs.extend(path.read_text(encoding="utf-8") for path in REFERENCES.glob("*.md"))
        combined = "\n".join(docs)

        self.assertIn('$skillDir\\scripts\\build_diagram.py', combined)
        self.assertIn('$skillDir\\scripts\\validate_diagram.py', combined)
        self.assertIn('$skillDir\\scripts\\generate_excalidraw.py', combined)
        self.assertIn('$skillDir\\scripts\\validate_excalidraw.py', combined)
        self.assertNotRegex(combined, r"python\s+scripts[\\/]")


if __name__ == "__main__":
    unittest.main()
