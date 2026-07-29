from __future__ import annotations


class EvaluationContextRepository:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, object]] = {}

    def store(self, key: str, payload: dict[str, object]) -> None:
        self._rows[key] = dict(payload)

    def fetch(self, key: str) -> dict[str, object] | None:
        row = self._rows.get(key)
        return dict(row) if row is not None else None
