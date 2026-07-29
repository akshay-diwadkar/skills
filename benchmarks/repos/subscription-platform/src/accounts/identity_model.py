from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountsIdentityModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"accounts:identity:{self.key}:{self.revision}"
