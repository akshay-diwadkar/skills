from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceAuditModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"persistence:audit:{self.key}:{self.revision}"
