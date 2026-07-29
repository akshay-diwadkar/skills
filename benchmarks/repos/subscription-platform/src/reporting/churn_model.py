from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportingChurnModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"reporting:churn:{self.key}:{self.revision}"
