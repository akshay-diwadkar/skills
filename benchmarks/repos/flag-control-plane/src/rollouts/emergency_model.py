from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RolloutsEmergencyModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"rollouts:emergency:{self.key}:{self.revision}"
