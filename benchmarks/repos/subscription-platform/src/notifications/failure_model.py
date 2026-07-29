from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationsFailureModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"notifications:failure:{self.key}:{self.revision}"
