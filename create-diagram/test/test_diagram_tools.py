from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "test" / "fixtures"
TEMPLATE = ROOT / "assets" / "html-diagram-template.html"
SKILL_DOC = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"
sys.path.insert(0, str(SCRIPTS))

import build_diagram  # noqa: E402
import validate_diagram  # noqa: E402
from _diagram_utils import _GEOMETRY_CONFIG, extract_diagram_data, js_obj_to_json  # noqa: E402


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
            notes = next(node for node in data["nodes"] if node["id"] == "notes")
            self.assertEqual(notes["label"], "Notes {JSON}")

    def test_html_template_uses_font_menu_instead_of_fit_button(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="font-menu-toggle"', text)
        self.assertIn('id="font-menu"', text)
        self.assertIn("function safeStorageGet(key)", text)
        self.assertIn("function safeStorageSet(key, value)", text)
        self.assertIn("function safeStorageRemove(key)", text)
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

    def test_builder_rejects_non_html_output_path(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            output_path = Path(tmp) / "diagram.txt"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must end with .html"):
                build_diagram.build_diagram(payload_path, output_path)

            self.assertFalse(output_path.exists())

    def test_builder_rejects_directory_output_path(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(IsADirectoryError):
                build_diagram.build_diagram(payload_path, Path(tmp))

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
            self.assertEqual(list(html_path.parent.glob(".diagram.html.*.tmp")), [])
            self.assertIn("const DIAGRAM_DATA =", html_path.read_text(encoding="utf-8"))

    def test_builder_cleans_unique_temp_file_after_write_failure(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            html_path = Path(tmp) / "diagram.html"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            original_replace = Path.replace

            def fail_replace(self, target):
                if self.name.startswith(".diagram.html.") and self.suffix == ".tmp":
                    raise OSError("simulated replace failure")
                return original_replace(self, target)

            try:
                Path.replace = fail_replace
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    build_diagram.build_diagram(payload_path, html_path, overwrite=True)
            finally:
                Path.replace = original_replace

            self.assertFalse(html_path.exists())
            self.assertEqual(list(Path(tmp).glob(".diagram.html.*.tmp")), [])

    def test_builder_inlines_runtime_assets(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            text = html_path.read_text(encoding="utf-8")

            self.assertIn('id="create-diagram-style" data-inline-asset="css/style.css"', text)
            self.assertIn('id="create-diagram-roughjs" data-inline-asset="roughjs.js"', text)
            self.assertIn("window.roughjs", text)
            self.assertNotIn('<link rel="stylesheet" href="css/style.css">', text)
            self.assertNotIn('<script src="roughjs.js"></script>', text)

            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_diagram.py"), str(html_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validate_diagram_cli_rejects_external_local_assets(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            text = html_path.read_text(encoding="utf-8")
            text = validate_diagram.INLINE_STYLE_RE.sub(
                '<link rel="stylesheet" href="css/style.css">',
                text,
            )
            text = validate_diagram.INLINE_ROUGHJS_RE.sub(
                '<script src="roughjs.js"></script>',
                text,
            )
            html_path.write_text(text, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_diagram.py"), str(html_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("embedded stylesheet", result.stderr)

    def test_builder_escapes_script_closing_sequences_in_data_and_metadata(self):
        payload = minimal_payload()
        injected = "</script><script>window.__xss_probe=1</script>"
        payload["diagram"]["nodes"][0]["label"] = injected
        payload["metadata"]["entities"][0]["name"] = injected

        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            text = html_path.read_text(encoding="utf-8")

            self.assertNotIn(injected, text)
            self.assertIn("<\\/script><script>window.__xss_probe=1<\\/script>", text)
            self.assertNotIn("<script>window.__xss_probe=1</script>", text)

            data = extract_diagram_data(text)
            metadata = validate_diagram.extract_agent_metadata(text, required=True)
            self.assertEqual(data["nodes"][0]["label"], injected)
            self.assertEqual(metadata["entities"][0]["name"], injected)

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

    def test_validate_diagram_cli_rejects_malformed_metadata(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            text = html_path.read_text(encoding="utf-8")
            text = re.sub(
                r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>',
                '<script type="application/json" id="agent-metadata">{not json}</script>',
                text,
                flags=re.S,
            )
            html_path.write_text(text, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_diagram.py"), str(html_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Could not parse #agent-metadata JSON", result.stderr)

    def test_validate_diagram_cli_rejects_empty_metadata(self):
        payload = minimal_payload()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = write_payload(payload, tmp)
            text = html_path.read_text(encoding="utf-8")
            text = re.sub(
                r'<script\s+type="application/json"\s+id="agent-metadata">.*?</script>',
                '<script type="application/json" id="agent-metadata"></script>',
                text,
                flags=re.S,
            )
            html_path.write_text(text, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_diagram.py"), str(html_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("#agent-metadata is empty", result.stderr)

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
            ]
            for command in commands:
                with self.subTest(command=command):
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_docs_use_anchored_script_commands(self):
        docs = [SKILL_DOC.read_text(encoding="utf-8")]
        docs.extend(path.read_text(encoding="utf-8") for path in REFERENCES.glob("*.md"))
        combined = "\n".join(docs)

        self.assertIn('/path/to/create-diagram/scripts/build_diagram.py', combined)
        self.assertIn('/path/to/create-diagram/scripts/validate_diagram.py', combined)
        self.assertNotIn('$skillDir\\scripts\\build_diagram.py', combined)
        self.assertNotIn('$skillDir\\scripts\\validate_diagram.py', combined)
        self.assertNotIn('$skillDir\\scripts\\generate_excalidraw.py', combined)
        self.assertNotIn('$skillDir\\scripts\\validate_excalidraw.py', combined)
        self.assertNotRegex(combined, r"python\s+scripts[\\/]")

    def test_template_uses_storage_helpers_for_local_storage_access(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        direct_storage_uses = [
            line for line in text.splitlines()
            if "localStorage." in line and "window.localStorage" not in line
        ]
        self.assertEqual(direct_storage_uses, [])

    def test_default_template_data_validates(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        data = extract_diagram_data(text)
        metadata = validate_diagram.extract_agent_metadata(text)
        errors, _warnings = validate_diagram.validate(data, metadata)
        self.assertEqual(errors, 0)

    def test_js_obj_to_json_parser_edge_cases(self):
        cases = [
            ("single quotes", "{'a':1}", '{"a":1}'),
            ("double quotes", '{"a":1}', '{"a":1}'),
            ("trailing comma", "{a:1,b:2,}", '{"a":1,"b":2}'),
            ("single-line comment", "{a:1,//comment\nb:2}", '{"a":1,"b":2}'),
            ("block comment", "{a:1,/*block*/b:2}", '{"a":1,"b":2}'),
            ("unquoted keys", "{key:42}", '{"key":42}'),
            ("nested braces", "{a:{b:[1,2]}}", '{"a":{"b":[1,2]}}'),
            ("mixed quotes", '{"a":\'hello\'}', '{"a":"hello"}'),
            ("inner double in single", "{a:'line \"quote\"'}",
             '{"a":"line \\"quote\\""}'),
            ("null/bool/num", "{a:null,b:true,c:3.14}",
             '{"a":null,"b":true,"c":3.14}'),
        ]
        for name, inp, expected in cases:
            with self.subTest(name=name):
                result = js_obj_to_json(inp)
                self.assertEqual(json.loads(result), json.loads(expected))

    def test_js_obj_to_json_rejects_backticks(self):
        with self.assertRaises(ValueError):
            js_obj_to_json("{a:`template`}")

    def test_layout_stress_large_diagram(self):
        node_count = 50
        edge_count = 49
        cluster_count = 5
        nodes = []
        metadata_entities = []
        edges = []
        metadata_relationships = []
        for i in range(node_count):
            nid = f"n{i}"
            nodes.append({
                "id": nid, "label": f"Node {i}", "type": "process",
                "description": f"Auto-generated node {i} for stress testing the layout algorithm.",
            })
            metadata_entities.append({
                "id": nid, "name": f"Node {i}", "type": "process",
                "description": f"Auto-generated node {i} for stress testing.",
                "evidence": "stress-test",
            })
        for i in range(edge_count):
            src = f"n{i}"
            tgt = f"n{i + 1}"
            edges.append({
                "sourceId": src, "targetId": tgt, "label": f"route-{i}",
                "evidence": "stress-test", "confidence": "observed",
            })
            metadata_relationships.append({
                "sourceId": src, "targetId": tgt, "label": f"route-{i}",
                "confidence": "observed", "evidence": "stress-test",
            })

        clusters = []
        for c in range(cluster_count):
            start = c * 10
            end = min(start + 10, node_count)
            clusters.append({
                "id": f"c-{c}",
                "label": f"Cluster {c}",
                "nodeIds": [f"n{i}" for i in range(start, end)],
            })

        payload = {
            "diagram": {
                "title": "Stress Test Diagram",
                "storageKey": "stress-test-v1",
                "audience": "test",
                "purpose": "Exercise the layout engine at scale.",
                "fidelity": "narrative-architecture",
                "takeaways": ["Large diagram stress test"],
                "nodes": nodes,
                "edges": edges,
                "clusters": clusters,
                "walkthrough": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "description": "The stress test diagram at a glance.",
                        "nodeIds": [nodes[0]["id"], nodes[-1]["id"]],
                    },
                ],
            },
            "metadata": {
                "audience": "test",
                "purpose": "Exercise the layout engine at scale.",
                "fidelity": "narrative-architecture",
                "entities": metadata_entities,
                "relationships": metadata_relationships,
                "assumptions": [],
                "omissions": [],
                "openQuestions": [],
                "agentInstructions": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "stress.html"
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            t0 = time.time()
            build_diagram.build_diagram(payload_path, html_path, overwrite=True)
            build_time = time.time() - t0

            data = extract_diagram_data(html_path.read_text(encoding="utf-8"))
            metadata = validate_diagram.extract_agent_metadata(html_path.read_text(encoding="utf-8"))
            errors, _warnings = validate_diagram.validate(data, metadata)
            self.assertEqual(errors, 0, f"Build time: {build_time:.2f}s")

    def test_constant_parity_between_python_and_js(self):
        config_path = ROOT / "assets" / "geometry-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        py = _GEOMETRY_CONFIG.copy()
        js = {}
        template_text = TEMPLATE.read_text(encoding="utf-8")
        for m in re.finditer(r"const (\w+)\s*=\s*([\d.]+)", template_text):
            name = m.group(1)
            if name not in js:
                js[name] = m.group(2)

        shared = set(py.keys()) & set(js.keys())
        self.assertGreater(len(shared), 5, "Too few shared constants to cross-verify")
        for name in sorted(shared):
            with self.subTest(constant=name):
                self.assertEqual(
                    str(py[name]), js[name],
                    f"Constant '{name}' differs: Python={py[name]}, JS={js[name]}",
                )

        json_keys = set(config.keys()) - {"_comment", "_js_only"}
        for name in sorted(json_keys):
            with self.subTest(constant=name + "_json"):
                self.assertIn(name, py, f"Constant '{name}' missing from Python module constants")


if __name__ == "__main__":
    unittest.main()
