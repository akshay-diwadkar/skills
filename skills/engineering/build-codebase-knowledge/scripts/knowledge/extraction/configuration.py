"""Configuration file extractor and command detector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


def extract_config_and_commands(
    repo_root: Path,
    rel_str: str,
    content: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Extract configuration metadata and evidence-backed repository commands.
    
    Returns:
        (config_entry, detected_commands)
    """
    fname = Path(rel_str).name.lower()
    config_entry: dict[str, Any] = {"path": rel_str, "role": "configuration"}
    commands: list[dict[str, str]] = []

    # Detect commands from pyproject.toml
    if fname == "pyproject.toml" and tomllib:
        try:
            data = tomllib.loads(content)
            if "tool" in data:
                if "pytest" in data["tool"] or "pytest" in content:
                    commands.append({"kind": "test", "cmd": "pytest", "source": rel_str})
                if "ruff" in data["tool"]:
                    commands.append({"kind": "lint", "cmd": "ruff check .", "source": rel_str})
                if "mypy" in data["tool"]:
                    commands.append({"kind": "typecheck", "cmd": "mypy .", "source": rel_str})
                if "poetry" in data["tool"].get("poetry", {}).get("scripts", {}):
                    commands.append({"kind": "build", "cmd": "poetry build", "source": rel_str})
        except Exception:
            pass

    # Detect commands from package.json
    elif fname == "package.json":
        try:
            data = json.loads(content)
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.append({"kind": "test", "cmd": "npm test", "source": rel_str})
            if "lint" in scripts:
                commands.append({"kind": "lint", "cmd": "npm run lint", "source": rel_str})
            if "build" in scripts:
                commands.append({"kind": "build", "cmd": "npm run build", "source": rel_str})
        except Exception:
            pass

    # Detect commands from Makefile
    elif fname in ["makefile", "gnumakefile"]:
        lines = content.splitlines()
        for line in lines:
            if line.startswith("test:"):
                commands.append({"kind": "test", "cmd": "make test", "source": rel_str})
            elif line.startswith("lint:"):
                commands.append({"kind": "lint", "cmd": "make lint", "source": rel_str})
            elif line.startswith("build:"):
                commands.append({"kind": "build", "cmd": "make build", "source": rel_str})

    # .env.example keys extraction (no values indexed!)
    elif fname.endswith(".env.example"):
        env_keys = []
        for line in content.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("#") and "=" in line_str:
                key = line_str.split("=", 1)[0].strip()
                env_keys.append(key)
        config_entry["keys"] = sorted(env_keys)

    return config_entry, commands
