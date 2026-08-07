#!/usr/bin/env python3
"""Semantics-preserving test-run instrumentation for the repository test baseline.

Loaded as a pytest plugin (``-p test_baseline_recorder``) by
``build_test_baseline.py``. It records:

- collected node IDs with their markers;
- per-node wall-clock duration buckets (setup + call + teardown);
- fixture-setup duration buckets;
- subprocess boundary events (``subprocess.run``/``call``/``check_call``/
  ``check_output``; direct ``Popen`` construction is NOT wrapped because
  stdlib subclasses it and wrapping would break them) and copy boundaries
  (``shutil.copytree`` and ``shutil.copy*``) with byte volume where
  measurable.

Every wrapped call is forwarded to the original implementation and its exact
return value is returned; measurement never alters test semantics. The recorder
writes one JSON document to the path in ``TEST_BASELINE_RECORDER_OUT`` at
session end.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import pytest
from test_baseline_utils import NodeMetrics, bucket_seconds


def _default_node_metrics() -> NodeMetrics:
    return {"bucket": ">120s", "subprocess": 0, "copy_bytes": 0, "copy_count": 0}



_state: dict[str, Any] = {
    "markers": {},
    "fixtures": [],
    "boundaries": [],
    "nodes": {},
    "current_node": "",
    "node_starts": {},
}


def _record_boundary(kind: str, detail: str, volume: int = 0) -> None:
    nodeid = _state["current_node"] or "collection"
    _state["boundaries"].append(
        {"nodeid": nodeid, "kind": kind, "detail": detail, "volume": volume}
    )
    if nodeid != "collection":
        node = _state["nodes"].setdefault(nodeid, _default_node_metrics())
        if kind == "subprocess":
            node["subprocess"] += 1
        else:
            node["copy_bytes"] += volume
            node["copy_count"] += 1


def _dir_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _file_bytes(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        pass
    return 0


def _wrap_callable(
    target: Callable[..., Any],
    kind: str,
    detail_fn: Callable[[tuple[Any, ...], dict[str, Any]], tuple[str, int]],
) -> Callable[..., Any]:
    @wraps(target)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            result = target(*args, **kwargs)
        except BaseException:
            _record_boundary(kind, "attempted")
            raise
        detail, volume = detail_fn(args, kwargs)
        _record_boundary(kind, detail, volume)
        return result

    return wrapper


_copy_depth = 0


def _wrap_copy_callable(
    target: Callable[..., Any],
    kind: str,
    detail_fn: Callable[[tuple[Any, ...], dict[str, Any]], tuple[str, int]],
) -> Callable[..., Any]:
    @wraps(target)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        global _copy_depth
        outer = _copy_depth == 0
        _copy_depth += 1
        try:
            result = target(*args, **kwargs)
        except BaseException:
            if outer:
                _record_boundary(kind, "attempted")
            raise
        finally:
            _copy_depth -= 1
        if outer:
            detail, volume = detail_fn(args, kwargs)
            _record_boundary(kind, detail, volume)
        return result

    return wrapper


def _command_detail(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, int]:
    raw = args[0] if args else kwargs.get("args", "")
    text = " ".join(str(part) for part in raw) if isinstance(raw, (list, tuple)) else str(raw)
    return text[:300], 0


def _copy_detail(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, int]:
    source = kwargs["src"] if "src" in kwargs else (args[0] if args else None)
    path = Path(str(source)) if source is not None else None
    volume = 0
    if path is not None:
        if path.is_dir():
            volume = _dir_bytes(path)
        else:
            volume = _file_bytes(path)
    return str(path) if path is not None else "", volume


def _copyfileobj_detail(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, int]:
    source = kwargs.get("fsrc", args[0] if args else None)
    volume = 0
    try:
        if source is not None:
            volume = os.fstat(source.fileno()).st_size
    except (AttributeError, OSError, ValueError):
        volume = 0
    return "copyfileobj", volume


def _zero_detail(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, int]:
    source = kwargs.get("src", args[0] if args else None)
    return str(source) if source is not None else "", 0


def _install_wraps() -> None:
    _wrap_module(subprocess, "subprocess", _wrap_callable, _command_detail)
    _wrap_module(shutil, "copy", _wrap_copy_callable, _copy_detail, ("copytree", "copy", "copy2", "copyfile"))
    _wrap_module(shutil, "copy", _wrap_copy_callable, _copyfileobj_detail, ("copyfileobj",))
    _wrap_module(shutil, "copy", _wrap_copy_callable, _zero_detail, ("copymode", "copystat"))


def _wrap_module(
    module: Any,
    kind: str,
    factory: Callable[..., Callable[..., Any]],
    detail_fn: Callable[[tuple[Any, ...], dict[str, Any]], tuple[str, int]],
    names: tuple[str, ...] | None = None,
) -> None:
    names = names or (
        ("run", "call", "check_call", "check_output")
        if kind == "subprocess"
        else ("copytree", "copy", "copy2", "copyfile", "copyfileobj", "copymode", "copystat")
    )
    for name in names:
        target = getattr(module, name, None)
        if callable(target):
            setattr(module, name, factory(target, kind, detail_fn))


def pytest_collection_modifyitems(session: Any, config: Any, items: list[Any]) -> None:
    for item in items:
        _state["markers"][item.nodeid] = sorted({marker.name for marker in item.iter_markers()})


def pytest_runtest_setup(item: Any) -> None:
    _state["current_node"] = item.nodeid
    _state["node_starts"][item.nodeid] = time.monotonic()


def pytest_runtest_teardown(item: Any, nextitem: Any) -> None:
    nodeid = item.nodeid
    started = _state["node_starts"].pop(nodeid, None)
    if started is not None:
        node = _state["nodes"].setdefault(nodeid, _default_node_metrics())
        node["bucket"] = bucket_seconds(time.monotonic() - started)
    if _state["current_node"] == nodeid:
        _state["current_node"] = ""


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: Any, request: Any) -> Any:
    started = time.monotonic()
    result = yield
    if hasattr(result, "get_result"):
        result = result.get_result()
    _state["fixtures"].append(
        {
            "fixture": getattr(
                fixturedef, "argname", getattr(fixturedef, "fixturename", "")
            ),
            "baseid": str(getattr(fixturedef, "baseid", getattr(fixturedef, "parentid", ""))),
            "bucket": bucket_seconds(time.monotonic() - started),
        }
    )
    return result


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    output = os.environ.get("TEST_BASELINE_RECORDER_OUT")
    if output:
        Path(output).write_text(
            json.dumps(_state, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )


_install_wraps()
