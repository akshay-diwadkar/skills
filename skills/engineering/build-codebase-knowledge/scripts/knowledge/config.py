"""Configuration loader and schema definition for build-codebase-knowledge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

DEFAULT_CONFIG: dict[str, Any] = {
    "output_dir": ".agent/knowledge",
    "max_context_lines": 120,
    "max_architecture_lines": 220,
    "max_summary_words": 12,
    "max_file_size_bytes": 1048576,  # 1MB
    "full_refresh_change_ratio": 0.20,
    "workflow_branch": "main",
    "workflow_runtime_repository": "https://github.com/akshay-diwadkar/skills.git",
    "workflow_runtime_revision": "09a44216123f4621a59ef965ccaa5aa96d3a2e5a",
    "workflow_runtime_directory": ".codebase-knowledge-runtime",
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
    "generated": ["**/generated/**", "**/*.gen.*", "**/adapters/**"],
    "weights": {
        "exact_symbol": 10.0,
        "exact_path": 10.0,
        "filename": 7.0,
        "subsystem": 5.0,
        "entry_point": 5.0,
        "dependency_neighbor": 3.0,
        "related_test": 4.0,
        "configuration": 4.0,
        "text_match": 2.0,
        "symbol_token": 5.0,
        "import_relationship": 3.0,
        "reverse_import_relationship": 3.0,
        "unsupported_extractor_penalty": -3.0,
        "stale_knowledge_penalty": -6.0,
        "generated_penalty": -8.0,
        "vendor_penalty": -10.0,
    },
}


def load_config(repo_root: Path | str) -> dict[str, Any]:
    """Load configuration from .codebase-knowledge.toml or return default config."""
    root = Path(repo_root).resolve()
    config_path = root / ".codebase-knowledge.toml"
    config = dict(DEFAULT_CONFIG)

    if config_path.is_file() and tomllib:
        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
                config.update(data)
        except Exception as exc:
            raise ValueError(f"Failed to parse configuration file {config_path}: {exc}") from exc

    weights = config.get("weights")
    if not isinstance(weights, dict) or any(not isinstance(value, (int, float)) for value in weights.values()):
        raise ValueError("weights must be a mapping of numeric values")
    return config
