#!/usr/bin/env python3
"""Deterministic failure-sample instrumentation for the repository test baseline.

Loaded as a pytest plugin (``-p test_baseline_failure_samples``) by
``build_test_baseline.py`` for the representative-failure sample run only. It
applies deterministic mutations to the committed data that selected real tests
consume, so those tests fail naturally on their own assertions and their actual
pytest diagnostics can be recorded.

Mutations are described in ``test-baseline-failure-samples.json`` (schema v1)
and applied only to the exact committed source paths named there:

- ``json-set`` / ``json-remove``: intercept ``Path.read_text`` on the named
  JSON file, mutate the parsed document (dotted ``target`` key path), and
  re-serialize;
- ``replace-string``: intercept ``Path.read_text`` on the named file and
  replace one literal substring;
- ``file-delete``: intercept ``shutil.copytree`` of the named source directory
  and unlink a file inside the freshly copied destination.

The mutation lives entirely in temporary/derived data; the working tree and
the test files are never modified. Interception matches on absolute resolved
paths, so reads of any other file are untouched.

Configuration comes from the environment:

- ``TEST_BASELINE_SAMPLES_PATH``: path to the samples manifest (required).
- ``TEST_BASELINE_SAMPLES_ROOT``: repository root against which manifest
  ``path`` values resolve (defaults to this file's repository root).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable

from test_baseline_utils import apply_failure_sample_text_mutation

_STATE: dict[str, Any] = {"by_source": {}, "root": None}


def _resolve_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_manifest() -> None:
    manifest_path = os.environ.get("TEST_BASELINE_SAMPLES_PATH")
    if not manifest_path:
        return
    _STATE["root"] = Path(os.environ.get("TEST_BASELINE_SAMPLES_ROOT") or _resolve_root())
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for sample in manifest.get("samples", []):
        mutation = sample.get("mutation")
        if not isinstance(mutation, dict) or not mutation.get("type") or not mutation.get("path"):
            continue
        source = _STATE["root"] / mutation["path"]
        _STATE["by_source"][str(source.resolve())] = dict(mutation)


def _mutate_text(text: str, mutation: dict[str, Any]) -> str:
    return apply_failure_sample_text_mutation(text, mutation)


def _install_read_text_wrap() -> None:
    original: Callable[..., Any] = Path.read_text

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        text = original(self, *args, **kwargs)
        mutation = _STATE["by_source"].get(str(self.resolve()))
        if mutation is not None:
            return _mutate_text(text, mutation)
        return text

    wrapper.__name__ = original.__name__
    wrapper.__qualname__ = original.__qualname__
    Path.read_text = wrapper  # type: ignore[method-assign]


def _install_copytree_wrap() -> None:
    original: Callable[..., Any] = shutil.copytree

    def wrapper(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(src, dst, *args, **kwargs)
        mutation = _STATE["by_source"].get(str(Path(src).resolve()))
        if mutation is not None and mutation.get("type") == "file-delete":
            target = Path(dst) / mutation["delete"]
            if target.exists():
                target.unlink()
        return result

    wrapper.__name__ = original.__name__
    wrapper.__qualname__ = original.__qualname__
    shutil.copytree = wrapper


_load_manifest()
_install_read_text_wrap()
_install_copytree_wrap()
