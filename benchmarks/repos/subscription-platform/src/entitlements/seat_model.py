from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementsSeatModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"entitlements:seat:{self.key}:{self.revision}"
