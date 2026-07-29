from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceFlagModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"persistence:flag:{self.key}:{self.revision}"
