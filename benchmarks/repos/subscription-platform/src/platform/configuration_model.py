from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformConfigurationModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"platform:configuration:{self.key}:{self.revision}"
