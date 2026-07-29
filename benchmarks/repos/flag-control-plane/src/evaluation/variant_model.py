from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationVariantModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"evaluation:variant:{self.key}:{self.revision}"
