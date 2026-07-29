from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BillingRenewalModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"billing:renewal:{self.key}:{self.revision}"
