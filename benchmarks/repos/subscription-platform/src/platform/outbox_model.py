from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformOutboxModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"platform:outbox:{self.key}:{self.revision}"
