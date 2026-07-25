"""Base interface and data models for language symbol and import extractors."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedSymbol:
    name: str
    qualified_name: str
    kind: str  # class, function, async-function, struct, type, export
    path: str
    line_start: int
    line_end: int
    subsystem: str
    docstring: str = ""


@dataclass
class ExtractedFileResult:
    path: str
    subsystem: str
    role: str  # source, test, configuration
    language: str
    symbols: list[ExtractedSymbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    file_hash: str = ""
    role_summary: str = ""
    extraction_confidence: str = "high"  # high, medium, low
    unknowns: list[str] = field(default_factory=list)
