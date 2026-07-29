from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiFlagModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"api:flag:{self.key}:{self.revision}"
