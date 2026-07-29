from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationsWebhookModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"notifications:webhook:{self.key}:{self.revision}"
