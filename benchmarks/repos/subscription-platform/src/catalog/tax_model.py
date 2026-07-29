from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTaxModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"catalog:tax:{self.key}:{self.revision}"
