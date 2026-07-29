from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountsAccessModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"accounts:access:{self.key}:{self.revision}"
