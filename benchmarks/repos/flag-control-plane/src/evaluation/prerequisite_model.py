from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationPrerequisiteModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"evaluation:prerequisite:{self.key}:{self.revision}"
