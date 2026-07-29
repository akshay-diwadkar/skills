from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogPlanModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"catalog:plan:{self.key}:{self.revision}"
