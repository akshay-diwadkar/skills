"""Shared utilities for plan validation scripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None
    is_warning: bool = False

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "is_warning": self.is_warning,
        }

    def __str__(self) -> str:
        prefix = "Warning" if self.is_warning else "Error"
        line_info = f" on line {self.line}" if self.line is not None else ""
        return f"{prefix} [{self.code}]{line_info}: {self.message}"


def read_plan(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def strip_fenced_code_blocks(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    in_fence = False
    for line in lines:
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            output.append("")
            continue
        output.append("" if in_fence else line)
    return "\n".join(output)
