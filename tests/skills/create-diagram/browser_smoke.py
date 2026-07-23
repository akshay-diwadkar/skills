"""Build and smoke-test create-diagram HTML in a real browser.

This script is intended for maintainers and CI. Normal skill usage does not
require Playwright.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "engineering" / "create-diagram"
RUNTIME_SCRIPTS = SKILL_ROOT / "scripts"
FIXTURE = DEV_DIR / "fixtures" / "complex.json"
sys.path.insert(0, str(RUNTIME_SCRIPTS))

import build_diagram  # noqa: E402


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for browser smoke testing. "
            "Install it with: python -m pip install playwright && python -m playwright install chromium"
        ) from exc
    return sync_playwright


def build_smoke_html(tmp_dir):
    payload_path = Path(tmp_dir) / "payload.json"
    output_path = Path(tmp_dir) / "diagram.html"
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    build_diagram.build_diagram(payload_path, output_path, overwrite=True)
    return output_path


def run_browser_smoke(html_path):
    sync_playwright = require_playwright()
    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.goto(html_path.resolve().as_uri(), wait_until="load")
            page.wait_for_selector("#nodes-layer .node-group", state="attached", timeout=10000)
            page.wait_for_selector("#edges-layer .edge-group", state="attached", timeout=10000)

            node_count = page.locator("#nodes-layer .node-group").count()
            edge_count = page.locator("#edges-layer .edge-group").count()
            if node_count < 3:
                raise AssertionError(f"Expected at least 3 rendered nodes, found {node_count}.")
            if edge_count < 3:
                raise AssertionError(f"Expected at least 3 rendered edges, found {edge_count}.")

            for selector in (
                "#title-display",
                "#zoom-in",
                "#zoom-out",
                "#zoom-fit-all",
                "#font-menu-toggle",
                "#theme-toggle",
                "#walkthrough-btn",
                "#legend-toggle",
            ):
                if not page.locator(selector).is_visible():
                    raise AssertionError(f"Required control is not visible: {selector}")

            warnings = page.locator("#warnings")
            if warnings.is_visible():
                warning_text = warnings.inner_text().strip()
                if warning_text:
                    raise AssertionError(f"Unexpected diagram warnings: {warning_text}")

            page.click("#walkthrough-btn")
            if not page.locator("#walkthrough-card").is_visible():
                raise AssertionError("Walkthrough card did not open.")
            page.click("#wt-card-next")
            page.click("#theme-toggle")
            page.click("#zoom-in")
            page.click("#zoom-out")
            page.click("#zoom-fit-all")

            if console_errors:
                raise AssertionError("Browser console errors:\n" + "\n".join(console_errors))
            if page_errors:
                raise AssertionError("Browser page errors:\n" + "\n".join(page_errors))
        finally:
            browser.close()


def main():
    try:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = build_smoke_html(tmp)
            run_browser_smoke(html_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Browser smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
