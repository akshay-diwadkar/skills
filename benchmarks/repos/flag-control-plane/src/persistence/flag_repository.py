from __future__ import annotations


class FlagRepository:
    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}

    def save(self, key: str, enabled: bool) -> None:
        self._flags[key] = enabled

    def get(self, key: str) -> bool | None:
        return self._flags.get(key)
