"""Stage B: Intent classification engine."""

from __future__ import annotations


def classify_intent(task: str) -> list[str]:
    """Classify engineering intent into one or more categories."""
    t_lower = task.lower()
    intents: set[str] = set()

    if any(k in t_lower for k in ["fix", "bug", "issue", "error", "crash", "fault", "exception"]):
        intents.add("bug")
    if any(k in t_lower for k in ["add", "feature", "create", "implement", "support", "new"]):
        intents.add("feature")
    if any(k in t_lower for k in ["test", "coverage", "spec", "pytest", "assertion"]):
        intents.add("test")
    if any(k in t_lower for k in ["config", "setting", "env", "yaml", "toml", "json", "ini"]):
        intents.add("configuration")
    if any(k in t_lower for k in ["refactor", "clean", "structure", "reorganize"]):
        intents.add("refactor")
    if any(k in t_lower for k in ["migrate", "migration", "upgrade", "schema"]):
        intents.add("migration")
    if any(k in t_lower for k in ["security", "auth", "permission", "password", "token", "rate limit"]):
        intents.add("security")
    if any(k in t_lower for k in ["optimize", "performance", "speed", "benchmark", "memory"]):
        intents.add("performance")
    if any(k in t_lower for k in ["dependency", "package", "lock", "pip", "npm"]):
        intents.add("dependency")
    if any(k in t_lower for k in ["doc", "readme", "comment", "guide"]):
        intents.add("documentation")
    if any(k in t_lower for k in ["ci", "workflow", "github action", "pipeline"]):
        intents.add("ci")
    if any(k in t_lower for k in ["remove", "delete", "cleanup", "prune"]):
        intents.add("cleanup")
    if any(k in t_lower for k in ["investigate", "audit", "trace", "find"]):
        intents.add("investigation")

    return sorted(list(intents)) if intents else ["feature"]
