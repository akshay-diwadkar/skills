from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportingExportModel:
    key: str
    revision: int = 1

    def stable_identity(self) -> str:
        return f"reporting:export:{self.key}:{self.revision}"
