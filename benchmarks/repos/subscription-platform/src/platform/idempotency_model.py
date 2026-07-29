from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformIdempotencyModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"platform:idempotency:{self.key}:{self.revision}"
