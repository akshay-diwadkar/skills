"""Local-only usage analytics for token efficiency measurement."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def record_session(
    knowledge_dir: Path,
    event: str,
    data: dict[str, Any],
) -> None:
    """Append one analytics event to the local analytics log."""
    log_path = knowledge_dir / "analytics.jsonl"
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        **data,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def summarize_sessions(knowledge_dir: Path) -> dict[str, Any]:
    """Summarize analytics from the local log."""
    log_path = knowledge_dir / "analytics.jsonl"
    if not log_path.is_file():
        return {"sessions": 0, "total_tokens_saved": 0}
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    resolve_events = [e for e in events if e.get("event") == "resolve"]
    return {
        "sessions": len(resolve_events),
        "total_tokens_saved": sum(e.get("tokens_saved", 0) for e in resolve_events),
        "avg_targets_returned": (
            round(sum(e.get("targets_returned", 0) for e in resolve_events) / max(len(resolve_events), 1), 1)
        ),
    }
