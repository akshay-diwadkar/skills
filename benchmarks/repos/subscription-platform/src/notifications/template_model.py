from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationsTemplateModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"notifications:template:{self.key}:{self.revision}"
