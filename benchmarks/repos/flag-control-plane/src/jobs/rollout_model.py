from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobsRolloutModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"jobs:rollout:{self.key}:{self.revision}"
