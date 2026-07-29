from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementsLicenseModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"entitlements:license:{self.key}:{self.revision}"
