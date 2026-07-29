from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementsFeatureModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"entitlements:feature:{self.key}:{self.revision}"
