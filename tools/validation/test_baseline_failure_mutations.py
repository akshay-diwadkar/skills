"""Pure failure-sample mutation and applicability validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KNOWN_MUTATION_TYPES = {"json-set", "json-remove", "replace-string", "file-delete"}


class MutationValidationError(ValueError):
    """Raised when a declared failure-sample mutation cannot be applied."""


def _json_index(value: Any, length: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MutationValidationError(f"JSON list index must be an integer, got {value!r}")
    if value < 0 or value >= length:
        raise MutationValidationError(f"JSON list index out of range: {value}")
    return value


def _json_target_parent(
    document: Any, target: Any, *, allow_missing_final_dict_key: bool
) -> tuple[Any, Any]:
    if not isinstance(target, list) or not target:
        raise MutationValidationError("JSON mutation target must be a non-empty list")
    cursor = document
    for key in target[:-1]:
        if isinstance(cursor, dict):
            if not isinstance(key, str):
                raise MutationValidationError(f"JSON object key must be a string, got {key!r}")
            try:
                cursor = cursor[key]
            except KeyError as exc:
                raise MutationValidationError(f"JSON parent path does not exist: {key!r}") from exc
        elif isinstance(cursor, list):
            cursor = cursor[_json_index(key, len(cursor))]
        else:
            raise MutationValidationError("JSON parent path traverses a non-container")

    final = target[-1]
    if isinstance(cursor, dict):
        if not isinstance(final, str):
            raise MutationValidationError(f"JSON object key must be a string, got {final!r}")
        if final not in cursor and not allow_missing_final_dict_key:
            raise MutationValidationError(f"JSON target does not exist: {final!r}")
    elif isinstance(cursor, list):
        final = _json_index(final, len(cursor))
    else:
        raise MutationValidationError("JSON mutation target ends at a non-container")
    return cursor, final


def apply_failure_sample_text_mutation(text: str, mutation: dict[str, Any]) -> str:
    """Apply one text/JSON mutation, rejecting ineffective declarations."""
    mutation_type = mutation.get("type")
    if mutation_type == "replace-string":
        old = mutation.get("old")
        new = mutation.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise MutationValidationError("replace-string old/new values must be strings")
        if not old or not new:
            raise MutationValidationError("replace-string old/new values must be non-empty")
        if old == new:
            raise MutationValidationError("replace-string old/new values must differ")
        if text.count(old) != 1:
            raise MutationValidationError("replace-string old value must occur exactly once")
        return text.replace(old, new, 1)

    if mutation_type == "json-set":
        if "value" not in mutation:
            raise MutationValidationError("json-set mutation is missing 'value'")
        document = json.loads(text)
        cursor, final = _json_target_parent(
            document, mutation.get("target"), allow_missing_final_dict_key=True
        )
        if isinstance(cursor, dict):
            existing = final in cursor
            current = cursor.get(final)
        else:
            existing = True
            current = cursor[final]
        if existing and current == mutation["value"]:
            raise MutationValidationError("json-set mutation would not change the document")
        cursor[final] = mutation["value"]
        return json.dumps(document, sort_keys=True, separators=(",", ":"))

    if mutation_type == "json-remove":
        if "index" in mutation:
            raise MutationValidationError("json-remove must encode its final key/index in 'target'")
        document = json.loads(text)
        cursor, final = _json_target_parent(
            document, mutation.get("target"), allow_missing_final_dict_key=False
        )
        del cursor[final]
        return json.dumps(document, sort_keys=True, separators=(",", ":"))

    raise MutationValidationError(f"unknown mutation type: {mutation_type!r}")


def resolve_file_delete_target(source: Path, delete: Any) -> Path:
    """Resolve a contained file-delete target without mutating the filesystem."""
    if not source.is_dir():
        raise MutationValidationError(f"file-delete source is not a directory: {source}")
    if not isinstance(delete, str) or not delete:
        raise MutationValidationError("file-delete mutation requires a non-empty 'delete' path")
    source_root = source.resolve()
    target = (source_root / delete).resolve()
    if target == source_root or source_root not in target.parents:
        raise MutationValidationError("file-delete target must stay inside the copied source")
    return target


def validate_failure_sample_mutation(root: Path, mutation: Any) -> None:
    """Prove one declared mutation can be applied and changes its source."""
    if not isinstance(mutation, dict):
        raise MutationValidationError("mutation must be an object")
    mutation_type = mutation.get("type")
    if mutation_type not in KNOWN_MUTATION_TYPES:
        raise MutationValidationError(f"unknown mutation type: {mutation_type!r}")
    source_value = mutation.get("path")
    if not isinstance(source_value, str) or not source_value:
        raise MutationValidationError("mutation source path must be a non-empty string")
    root_resolved = root.resolve()
    source = (root_resolved / source_value).resolve()
    if source != root_resolved and root_resolved not in source.parents:
        raise MutationValidationError("mutation source must stay inside the repository root")
    if not source.exists():
        raise MutationValidationError(f"mutation source does not exist: {source_value!r}")

    if mutation_type in {"json-set", "json-remove", "replace-string"}:
        if not source.is_file():
            raise MutationValidationError("text mutation source must be a regular file")
        try:
            original = source.read_text(encoding="utf-8")
            mutated = apply_failure_sample_text_mutation(original, mutation)
        except MutationValidationError:
            raise
        except (OSError, TypeError, ValueError) as exc:
            raise MutationValidationError(f"mutation cannot be applied: {exc}") from exc
        if mutation_type in {"json-set", "json-remove"}:
            if json.loads(mutated) == json.loads(original):
                raise MutationValidationError(f"{mutation_type} mutation would not change the document")
        elif mutated == original:
            raise MutationValidationError("replace-string mutation would not change its source")
        return

    target = resolve_file_delete_target(source, mutation.get("delete"))
    if not target.is_file():
        raise MutationValidationError(f"file-delete target does not exist as a file: {mutation.get('delete')!r}")
