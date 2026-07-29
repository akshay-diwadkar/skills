from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BillingCreditModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"billing:credit:{self.key}:{self.revision}"
