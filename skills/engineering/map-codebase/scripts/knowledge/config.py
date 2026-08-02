"""Configuration loader and schema definition for map-codebase."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "output_dir": ".agent/knowledge",
    "max_context_lines": 120,
    "max_file_size_bytes": 1048576,  # 1MB
    "full_refresh_change_ratio": 0.20,
    "include_untracked": True,
    "confidence_margin": 2.0,
    # An empty include list means every safe, tracked repository file.  Projects
    # should not disappear from the index merely because they use an unfamiliar
    # top-level directory name.
    "include": [],
    "exclude": [
        "**/node_modules/**",
        "**/vendor/**",
        "**/dist/**",
        "**/build/**",
        "**/.git/**",
        "**/.agent/**",
        "**/__pycache__/**",
        "**/*.min.js",
        "**/*.pyc",
        "**/.venv/**",
        "**/venv/**",
        "**/.mypy_cache/**",
        "**/.pytest_cache/**",
        "**/.ruff_cache/**",
    ],
        "generated": ["**/generated/**", "**/*.gen.*"],
    "weights": {
        "exact_symbol": 10.0,
        "exact_path": 10.0,
        "filename": 7.0,
        "subsystem": 5.0,
        "entry_point": 5.0,
        "related_test": 4.0,
        "configuration": 4.0,
        "text_match": 2.0,
        "synonym_token": 1.5,
        "symbol_token": 5.0,
        "import_relationship": 3.0,
        "reverse_import_relationship": 3.0,
        "unsupported_extractor_penalty": -3.0,
        "stale_knowledge_penalty": -6.0,
        "generated_penalty": -8.0,
        "vendor_penalty": -10.0,
    },
}

REQUIRED_WEIGHTS = frozenset(DEFAULT_CONFIG["weights"])
PENALTY_WEIGHTS = frozenset(key for key in REQUIRED_WEIGHTS if key.endswith("_penalty"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(config: dict[str, Any]) -> None:
    output = config.get("output_dir")
    if not isinstance(output, str) or not output.strip() or Path(output).is_absolute() or ".." in Path(output).parts:
        raise ValueError("output_dir must be a non-empty, repository-relative safe path")
    for key in ("max_context_lines", "max_file_size_bytes"):
        if not isinstance(config.get(key), int) or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    ratio = config.get("full_refresh_change_ratio")
    if not isinstance(ratio, (int, float)) or not 0 < ratio <= 1:
        raise ValueError("full_refresh_change_ratio must be greater than 0 and at most 1")
    if not isinstance(config.get("include_untracked"), bool):
        raise ValueError("include_untracked must be boolean")
    margin = config.get("confidence_margin")
    if not isinstance(margin, (int, float)) or isinstance(margin, bool) or margin < 0:
        raise ValueError("confidence_margin must be a non-negative number")
    for key in ("include", "exclude", "generated"):
        if not isinstance(config.get(key), list) or any(not isinstance(item, str) for item in config[key]):
            raise ValueError(f"{key} must be a list of strings")
    weights = config.get("weights")
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping of numeric values")
    missing = REQUIRED_WEIGHTS - set(weights)
    if missing:
        raise ValueError(f"weights is missing required values: {', '.join(sorted(missing))}")
    for key, value in weights.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"weights.{key} must be numeric")
        if key in PENALTY_WEIGHTS and value > 0:
            raise ValueError(f"weights.{key} must be non-positive")
        if key not in PENALTY_WEIGHTS and value < 0:
            raise ValueError(f"weights.{key} must be non-negative")


def load_config(repo_root: Path | str) -> dict[str, Any]:
    """Load configuration from .codebase-knowledge.toml or return default config."""
    root = Path(repo_root).resolve()
    config_path = root / ".codebase-knowledge.toml"
    config = _deep_merge(DEFAULT_CONFIG, {})

    if config_path.is_file():
        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
                if not isinstance(data, dict):
                    raise ValueError("configuration root must be a table")
                config = _deep_merge(config, data)
        except Exception as exc:
            raise ValueError(f"Failed to parse configuration file {config_path}: {exc}") from exc

    _validate(config)
    return config


def resolve_knowledge_directory(repo_root: Path | str, output_dir: Path | str | None, config: dict[str, Any]) -> Path:
    """Resolve the one safe runtime output location for a command."""
    root = Path(repo_root).resolve()
    candidate = Path(output_dir) if output_dir is not None else Path(config["output_dir"])
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("knowledge output must be inside repository") from exc
    return resolved
