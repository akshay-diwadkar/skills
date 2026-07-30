"""Intent compatibility helpers."""

from __future__ import annotations

from resolver.schemas import TaskQuery


def requested_phase_intents(query: TaskQuery) -> tuple[bool, bool, bool]:
    return (
        "ownership" in query.intents,
        "constraint" in query.intents,
        "impact" in query.intents,
    )
