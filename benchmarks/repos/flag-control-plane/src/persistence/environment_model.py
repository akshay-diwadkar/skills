from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceEnvironmentModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"persistence:environment:{self.key}:{self.revision}"
