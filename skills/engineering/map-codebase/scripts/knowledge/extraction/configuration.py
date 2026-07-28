"""Configuration file extractor and command detector."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


def _flatten_keys(value: Any, prefix: str = "") -> list[str]:
    """Return deterministic dotted keys for nested mappings and lists."""
    keys: list[str] = []
    if isinstance(value, dict):
        for raw_key, child in sorted(value.items(), key=lambda item: str(item[0])):
            key = str(raw_key)
            dotted = ".".join(part for part in (prefix, key) if part)
            keys.append(dotted)
            keys.extend(_flatten_keys(child, dotted))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_flatten_keys(child, prefix))
    return keys


def _structured_text_keys(rel_str: str, content: str) -> list[str]:
    """Extract dotted keys from lightweight configuration syntaxes."""
    suffix = Path(rel_str).suffix.lower()
    name = Path(rel_str).name.lower()
    keys: list[str] = []
    if suffix in {".toml", ".ini", ".cfg"}:
        section = ""
        for line in content.splitlines():
            section_match = re.match(r"\s*\[([^]]+)\]", line)
            if section_match:
                section = section_match.group(1).strip()
                keys.append(section)
                continue
            key_match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*[=:]", line)
            if key_match and not line.lstrip().startswith(("#", ";")):
                keys.append(".".join(part for part in (section, key_match.group(1)) if part))
    elif suffix in {".yaml", ".yml"}:
        ancestors: list[tuple[int, str]] = []
        for line in content.splitlines():
            match = re.match(r"^(\s*)([A-Za-z0-9_.-]+):", line)
            if not match or line.lstrip().startswith("#"):
                continue
            indent, key = len(match.group(1).expandtabs(2)), match.group(2)
            while ancestors and ancestors[-1][0] >= indent:
                ancestors.pop()
            dotted = ".".join([item[1] for item in ancestors] + [key])
            keys.append(dotted)
            ancestors.append((indent, key))
    elif name in {"makefile", "gnumakefile"}:
        for line in content.splitlines():
            match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", line)
            if match:
                keys.append(match.group(1))
    return keys


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
            config_entry["keys"] = sorted(set(_flatten_keys(data)))
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
            config_entry["keys"] = sorted(set(_flatten_keys(data)))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                commands.append({"kind": "test", "cmd": "npm test", "source": rel_str})
            if "lint" in scripts:
                commands.append({"kind": "lint", "cmd": "npm run lint", "source": rel_str})
            if "build" in scripts:
                commands.append({"kind": "build", "cmd": "npm run build", "source": rel_str})
        except Exception:
            pass

    elif fname.startswith("tsconfig") and fname.endswith(".json"):
        try:
            config_entry["keys"] = sorted(set(_flatten_keys(json.loads(content))))
        except Exception:
            pass

    elif Path(rel_str).suffix.lower() == ".json":
        try:
            config_entry["keys"] = sorted(set(_flatten_keys(json.loads(content))))
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
        config_entry["keys"] = sorted(set(_structured_text_keys(rel_str, content)))

    # .env.example keys extraction (no values indexed!)
    elif fname.endswith(".env.example"):
        env_keys = []
        for line in content.splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("#") and "=" in line_str:
                key = line_str.split("=", 1)[0].strip()
                env_keys.append(key)
        config_entry["keys"] = sorted(env_keys)

    if "keys" not in config_entry:
        keys = _structured_text_keys(rel_str, content)
        if keys:
            config_entry["keys"] = sorted(set(keys))

    return config_entry, commands
