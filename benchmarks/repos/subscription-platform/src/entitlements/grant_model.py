from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementsGrantModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"entitlements:grant:{self.key}:{self.revision}"
