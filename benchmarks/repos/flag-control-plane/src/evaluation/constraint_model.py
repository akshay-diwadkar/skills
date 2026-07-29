from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationConstraintModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"evaluation:constraint:{self.key}:{self.revision}"
