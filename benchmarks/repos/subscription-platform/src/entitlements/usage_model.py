from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementsUsageModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"entitlements:usage:{self.key}:{self.revision}"
