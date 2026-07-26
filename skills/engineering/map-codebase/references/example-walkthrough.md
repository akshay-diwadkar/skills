# Worked Resolver Walkthrough

This walkthrough uses real output from this repository. The JSON blocks retain only the fields needed to demonstrate the workflow.

## 1. Check Freshness

```bash
python skills/engineering/map-codebase/scripts/cli.py status --repo-root . --format json
```

```json
{
  "status": "partially-stale",
  "reason": "4 repository changes.",
  "changed_files": [
    "skills/engineering/map-codebase/SKILL.md",
    "skills/engineering/map-codebase/references/example-walkthrough.md",
    "skills/engineering/map-codebase/references/integration-guide.md",
    "skills/engineering/map-codebase/references/knowledge-contract.md"
  ],
  "requires_full_rebuild": false,
  "revision_changed": false,
  "repository_metadata_changed": true,
  "current_revision": "c96b5dc0f49771faeb89137e63be689ae56b1d74",
  "detection_mode": "git-diff"
}
```

## 2. Refresh the Reported Delta

```bash
python skills/engineering/map-codebase/scripts/cli.py refresh \
  --repo-root . \
  --changed-file skills/engineering/map-codebase/SKILL.md \
  --changed-file skills/engineering/map-codebase/references/example-walkthrough.md \
  --changed-file skills/engineering/map-codebase/references/integration-guide.md \
  --changed-file skills/engineering/map-codebase/references/knowledge-contract.md
```

## 3. Resolve Phase 1

```bash
python skills/engineering/map-codebase/scripts/cli.py resolve \
  "Fix task ownership classification in classify_task_intent without changing the resolver output schema" \
  --repo-root . --phase 1 --format json
```

```json
{
  "task": "Fix task ownership classification in classify_task_intent without changing the resolver output schema",
  "phase": 1,
  "knowledge_freshness": "fresh",
  "task_intent": {
    "primary_role": "source",
    "secondary_roles": [],
    "reasons": [
      "explicit indexed symbol matched skills/engineering/map-codebase/scripts/resolve_task.py"
    ]
  },
  "confidence": {
    "level": "high",
    "score": 80.0,
    "reasons": [
      "exact symbol matched classify_task_intent",
      "direct test relationship points to tests/skills/map-codebase/test_finalization_lifecycle.py",
      "direct test relationship points to tests/skills/map-codebase/test_release_regressions.py",
      "direct test relationship points to tests/skills/map-codebase/test_resolve_task.py",
      "direct test relationship points to tests/skills/map-codebase/test_resolver_engine.py",
      "direct test relationship points to tests/skills/map-codebase/test_resolver_integrity.py",
      "top candidate exceeds the configured confidence margin"
    ],
    "uncertainties": []
  },
  "targets": [
    {
      "path": "skills/engineering/map-codebase/scripts/resolve_task.py",
      "symbol": "classify_task_intent",
      "start_line": 122,
      "end_line": 190,
      "role": "source",
      "question": "Does classify_task_intent own the requested behavior?"
    }
  ],
  "question": "Which likely task owner owns the requested behavior or constraint?",
  "stop_condition": "Stop when ownership and the source contract are verified.",
  "expansion_triggers": [
    "ownership remains ambiguous",
    "source contradicts the index"
  ]
}
```

Read the returned source range, answer the phase question, and stop unless an expansion trigger applies.
