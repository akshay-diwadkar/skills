from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformHealthModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"platform:health:{self.key}:{self.revision}"
