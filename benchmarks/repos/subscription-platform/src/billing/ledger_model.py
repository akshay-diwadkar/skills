from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BillingLedgerModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"billing:ledger:{self.key}:{self.revision}"
