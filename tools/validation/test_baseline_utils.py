"""Shared utilities for test system baseline tools.

Holds timing bucket definitions, table-driven path-to-layer resolution,
and TypedDict structures shared between build_test_baseline and
test_baseline_recorder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, TypedDict

BUCKET_EDGES = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
BUCKET_LABELS = tuple(f"{edge:g}s" for edge in BUCKET_EDGES)

FIXTURE_PATH_MARKERS = (
    "/evals/",
    "/eval/",
    "/fixtures/",
    "/repos/",
    "/worked-example-fixtures",
    "/static-regression-cases",
)

# Table-driven prefix mapping to eliminate repeated switch cascades
PATH_LAYER_MAP: list[tuple[str, str]] = [
    ("tests/skills/", "skill-local"),
    ("skills/", "skill-local"),
    ("tests/repository/", "repository-policy"),
    ("repository/", "repository-policy"),
    ("tests/shared/", "shared-runtime"),
    ("shared/", "shared-runtime"),
    ("tests/skill_protocol/", "shared-protocol"),
    ("skill_protocol/", "shared-protocol"),
    ("tests/classification/", "classification"),
    ("classification/", "classification"),
    ("tests/integration/", "installed-execution"),
    ("integration/", "installed-execution"),
    ("tests/benchmarks/", "benchmark-fixture"),
    ("benchmarks/", "benchmark-fixture"),
]


class NodeMetrics(TypedDict):
    """Runtime metrics tracked per test node."""

    bucket: str
    subprocess: int
    copy_bytes: int
    copy_count: int


def bucket_seconds(seconds: float) -> str:
    """Return the bucket label for a given duration in seconds."""
    for index, edge in enumerate(BUCKET_EDGES):
        if seconds < edge:
            return BUCKET_LABELS[max(index - 1, 0)]
    return f">{BUCKET_EDGES[-1]:g}s"


def bucket_index(label: str) -> int:
    """Return the ordinal index of a bucket label for median calculations."""
    try:
        return BUCKET_LABELS.index(label)
    except ValueError:
        return len(BUCKET_LABELS) - 1


def median_bucket(labels: Sequence[str]) -> str:
    """Compute the median duration bucket label from a collection of labels."""
    if not labels:
        return BUCKET_LABELS[0]
    indices = sorted(bucket_index(label) for label in labels)
    return BUCKET_LABELS[indices[(len(indices) - 1) // 2]]


# Tool invocations that install packages, keyed by executable name (lowercase
# basename) to the subcommands that count as installation; an empty set means
# any invocation of the tool counts as an installer boundary.
INSTALLER_COMMANDS: dict[str, set[str]] = {
    "pip": {"install"},
    "pip3": {"install"},
    "uv": {"pip", "sync", "add"},
    "conda": {"install"},
    "poetry": {"install", "add"},
    "npx": set(),
    "npm": {"install", "ci", "add", "uninstall"},
    "yarn": {"install", "add"},
    "pnpm": {"install", "add"},
    "dotnet": {"restore", "add"},
    "go": {"mod", "install"},
    "cargo": {"install"},
    "bundle": {"install"},
    "gem": {"install"},
    "brew": {"install"},
}

# External tools whose invocation is an external-tool boundary; an empty set
# means any invocation of the tool counts.
EXTERNAL_TOOL_COMMANDS: dict[str, set[str]] = {
    "git": set(),
    "node": set(),
    "npm": {"run", "test", "build", "exec"},
    "yarn": {"run", "test"},
    "pnpm": {"run", "test"},
    "dotnet": {"test", "run", "build"},
    "go": {"test", "build", "run"},
    "cargo": {"test", "build", "run"},
    "gradle": set(),
    "gradlew": set(),
    "python": set(),
    "python3": set(),
    "sh": set(),
    "bash": set(),
    "make": set(),
    "cmake": set(),
    "rg": set(),
    "gh": set(),
}

# Exe names treated as network boundaries when invoked via subprocess.
NETWORK_SUBPROCESS_TOOLS = {"curl", "wget"}

# Env-var name hints that classify a credential boundary.
CREDENTIAL_NAME_HINTS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")

# Python modules that read credentials from the environment.
CREDENTIAL_MODULES = ("keyring", "netrc", "google.oauth2", "boto3")


def classify_subprocess_command(tokens: Sequence[str]) -> set[str]:
    """Classify a subprocess command token list into semantic boundary kinds.

    Returns an empty set for plain subprocess invocations that are neither an
    installer, an external tool, nor a network tool.
    """
    if not tokens:
        return set()
    tool = str(tokens[0]).lower()
    if tool.endswith((".exe", ".cmd", ".bat")):
        tool = Path(tool).stem.lower()
    else:
        tool = Path(tool).stem.lower() or tool
    rest = [str(token).lower() for token in tokens[1:]]
    if tool == "python" or tool == "python3":
        module_index = None
        for index, token in enumerate(rest):
            if token == "-m" and index + 1 < len(rest):
                module_index = index + 1
                break
        if module_index is not None:
            module = rest[module_index]
            if module in ("pip", "pip3", "uv", "poetry"):
                return {"installer"}
            return {"external-tool"}
    if tool in INSTALLER_COMMANDS:
        subcommands = INSTALLER_COMMANDS[tool]
        if not subcommands or any(token in subcommands for token in rest):
            return {"installer"}
        if tool in EXTERNAL_TOOL_COMMANDS:
            return {"external-tool"}
    if tool in EXTERNAL_TOOL_COMMANDS:
        subcommands = EXTERNAL_TOOL_COMMANDS[tool]
        if not subcommands or any(token in subcommands for token in rest):
            return {"external-tool"}
    if tool in NETWORK_SUBPROCESS_TOOLS:
        return {"network"}
    return set()


def env_name_is_credential(name: str) -> bool:
    """Return whether an environment variable name reads like a credential."""
    upper = name.upper()
    return any(hint in upper for hint in CREDENTIAL_NAME_HINTS)


def derive_layer_from_path(relative_path: str) -> str:
    """Derive test layer from a relative file path using table-driven prefix matching."""
    lowered = relative_path.replace("\\", "/").lower()
    if lowered.startswith("skills") and any(m in lowered for m in FIXTURE_PATH_MARKERS):
        return "fixture-repository"
    for prefix, layer in PATH_LAYER_MAP:
        if lowered.startswith(prefix) or f"/{prefix}" in lowered:
            return layer
    return "repository-policy"
