from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiEnvironmentModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"api:environment:{self.key}:{self.revision}"
