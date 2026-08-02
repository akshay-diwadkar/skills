"""Relationship graph builder for internal imports, reverse imports, and test mappings."""

from __future__ import annotations

import posixpath
from collections import defaultdict
from pathlib import Path
from typing import Any


def resolve_import_to_path(
    import_str: str,
    indexed_files: set[str],
    current_file: str,
    suffix_index: dict[str, tuple[str, ...]] | None = None,
) -> str | None:
    """Attempt to resolve an import string to an indexed internal repository file path.

    Returns:
        rel_path if resolved to an internal file, or None if external/unresolved.
    """
    raw = import_str.strip().replace("\\", "/")
    known_suffixes = (".tsx", ".jsx", ".py", ".ts", ".js", ".go", ".rs")
    for suffix in known_suffixes:
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
            break

    # Relative JavaScript/TypeScript imports commonly name the emitted `.js`
    # file even though the indexed owner is the `.ts` source. Resolve the
    # relative path before considering dotted Python/module notation.
    curr_dir = str(Path(current_file).parent).replace("\\", "/")
    if raw.startswith(("./", "../")):
        cleaned = posixpath.normpath(posixpath.join(curr_dir, raw))
    else:
        cleaned = raw.strip("./")
        if "/" not in cleaned:
            cleaned = cleaned.replace(".", "/")

    # Try exact match or suffix match
    for ext in [".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"]:
        candidate = f"{cleaned}{ext}"
        if candidate in indexed_files:
            return candidate

        # Try relative to current file's directory
        if curr_dir and curr_dir != ".":
            rel_candidate = f"{curr_dir}/{cleaned}{ext}"
            if rel_candidate in indexed_files:
                return rel_candidate

        # Try a pre-indexed suffix match (e.g. src/auth/service.py for auth.service).
        if suffix_index is not None:
            matches = suffix_index.get(candidate, ())
            if matches:
                return matches[0]
        else:
            for indexed in sorted(indexed_files):
                if indexed.endswith(candidate) or indexed == candidate:
                    return indexed

    return None


def build_relationship_graph(
    files: list[dict[str, Any]],
    tests: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build bidirectional relationship graph across all indexed files.

    Returns:
        (updated_files, updated_dependencies, updated_tests)
    """
    indexed_path_set = {f["path"] for f in files}
    suffix_paths: dict[str, list[str]] = defaultdict(list)
    for indexed_path in sorted(indexed_path_set):
        parts = indexed_path.split("/")
        for index in range(len(parts)):
            suffix_paths["/".join(parts[index:])].append(indexed_path)
    suffix_index = {key: tuple(paths) for key, paths in suffix_paths.items()}
    import_map: dict[str, set[str]] = {f["path"]: set() for f in files}
    reverse_import_map: dict[str, set[str]] = {f["path"]: set() for f in files}
    dependencies: list[dict[str, Any]] = []

    # 1. Resolve forward imports and populate reverse imports
    for f in files:
        path = f["path"]
        raw_imports = f.get("imports", [])
        resolved_internal: set[str] = set()

        for imp in raw_imports:
            resolved = resolve_import_to_path(imp, indexed_path_set, path, suffix_index)
            if resolved and resolved != path:
                resolved_internal.add(resolved)
                reverse_import_map[resolved].add(path)
                dependencies.append(
                    {
                        "from": path,
                        "to": resolved,
                        "source": path,
                        "target": resolved,
                        "kind": "import",
                    }
                )

        import_map[path] = resolved_internal
        f["imports"] = sorted(list(resolved_internal))

    # 2. Update imported_by for every file
    for f in files:
        path = f["path"]
        f["imported_by"] = sorted(list(reverse_import_map[path]))

    # 3. Source-to-Test and Test-to-Source mappings
    updated_tests: list[dict[str, Any]] = []
    file_by_path = {f["path"]: f for f in files}

    for f in files:
        if f.get("role") == "test":
            test_path = f["path"]
            targets: set[str] = set()

            # Direct target from imports
            for imp_target in f.get("imports", []):
                if file_by_path.get(imp_target, {}).get("role") == "source":
                    targets.add(imp_target)

            # Target from filename conventions (test_foo.py -> foo.py)
            stem = Path(test_path).stem
            if stem.startswith("test_"):
                stem = stem[5:]
            for suffix in ("_test", ".test", "-test", "Test"):
                if stem.endswith(suffix):
                    stem = stem[: -len(suffix)]
                    break
            for src_path in indexed_path_set:
                if file_by_path.get(src_path, {}).get("role") == "source":
                    if Path(src_path).stem.casefold() == stem.casefold():
                        targets.add(src_path)

            target_list = sorted(list(targets))
            updated_tests.append({"path": test_path, "targets": target_list})

            # Update source file's tests field
            for target_path in target_list:
                if target_path in file_by_path:
                    src_tests = set(file_by_path[target_path].get("tests", []))
                    src_tests.add(test_path)
                    file_by_path[target_path]["tests"] = sorted(list(src_tests))

    # Sort dependencies for determinism
    dependencies_sorted = sorted(dependencies, key=lambda d: (d["source"], d["target"]))
    tests_sorted = sorted(updated_tests, key=lambda t: t["path"])

    return files, dependencies_sorted, tests_sorted
