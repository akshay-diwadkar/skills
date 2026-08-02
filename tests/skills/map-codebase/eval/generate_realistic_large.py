"""Regenerate the committed realistic-large resolver fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

def generate(root: Path) -> None:
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"fixture output must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for package in ("domain", "services", "repositories", "adapters"):
        directory = root / "src" / package
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").write_text("", encoding="utf-8")
        for index in range(45):
            prior = f"component_{index - 1:03d}" if index else None
            function = f"{package}_value_{index:03d}"
            prior_function = f"{package}_value_{index - 1:03d}"
            imports = (
                f"from src.{package}.{prior} import {prior_function}  # noqa: F401\n\n\n"
                if prior
                else ""
            )
            (directory / f"component_{index:03d}.py").write_text(
                imports
                + f"def {function}(amount: int) -> int:\n"
                + f"    \"\"\"Return deterministic {package} component {index:03d} output.\"\"\"\n"
                + f"    return amount + {index}\n",
                encoding="utf-8", newline="\n",
            )

    extractor = root / "src" / "extractors"
    extractor.mkdir(parents=True, exist_ok=True)
    (extractor / "__init__.py").write_text("", encoding="utf-8")
    (extractor / "javascript_extractor.py").write_text(
        "def extract_arrow_function_exports(source: str) -> list[str]:\n"
        "    \"\"\"Return exported JavaScript arrow-function declarations.\"\"\"\n"
        "    return [line for line in source.splitlines() if \"export \" in line and \"=>\" in line]\n",
        encoding="utf-8", newline="\n",
    )
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "script.py").write_text(
        "def export_script(value: str) -> str:\n    return value\n",
        encoding="utf-8", newline="\n",
    )
    services = root / "src" / "billing"
    services.mkdir(parents=True, exist_ok=True)
    (services / "__init__.py").write_text("", encoding="utf-8")
    (services / "invoice_service.py").write_text(
        "from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal\n\n"
        "_SUPPORTED_ROUNDING = (ROUND_DOWN, ROUND_HALF_UP)\n\n"
        "def round_invoice_total(value: str) -> str:\n"
        "    \"\"\"Round an invoice total to two decimal places.\"\"\"\n"
        "    return str(Decimal(value).quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP))\n",
        encoding="utf-8", newline="\n",
    )

    checks = root / "tests"
    checks.mkdir(parents=True, exist_ok=True)
    (checks / "check_extractor.py").write_text(
        "from src.extractors.javascript_extractor import extract_arrow_function_exports\n"
        "\n"
        "assert extract_arrow_function_exports('export const value = () => 1;') == ['export const value = () => 1;']\n",
        encoding="utf-8", newline="\n",
    )
    (checks / "check_invoice.py").write_text(
        "from src.billing.invoice_service import round_invoice_total\n"
        "\n"
        "assert round_invoice_total('10.125') == '10.13'\n",
        encoding="utf-8", newline="\n",
    )
    for index in range(20):
        (checks / f"check_component_{index:03d}.py").write_text(
            f"from src.domain.component_{index:03d} import domain_value_{index:03d}\n"
            "\n"
            f"assert domain_value_{index:03d}(1) == {index + 1}\n",
            encoding="utf-8", newline="\n",
        )

    configs = root / "config"
    configs.mkdir(parents=True, exist_ok=True)
    for index in range(6):
        (configs / f"service-{index}.json").write_text(
            json.dumps({"service": {"name": f"component-{index}", "timeout": 30}}, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    (root / "pyproject.toml").write_text(
        "[tool.ruff]\nline-length = 100\n\n[tool.pytest.ini_options]\naddopts = '-q'\n",
        encoding="utf-8", newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    generate(parser.parse_args().output)
