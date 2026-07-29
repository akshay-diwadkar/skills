from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogOfferModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"catalog:offer:{self.key}:{self.revision}"
