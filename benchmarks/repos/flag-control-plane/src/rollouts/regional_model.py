from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RolloutsRegionalModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"rollouts:regional:{self.key}:{self.revision}"
