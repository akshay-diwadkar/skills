from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceRevisionModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"persistence:revision:{self.key}:{self.revision}"
