from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiEvaluationModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"api:evaluation:{self.key}:{self.revision}"
