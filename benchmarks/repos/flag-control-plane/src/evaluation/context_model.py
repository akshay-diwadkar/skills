from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationContextModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"evaluation:context:{self.key}:{self.revision}"
