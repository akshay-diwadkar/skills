# Worked Resolver Walkthrough

Use this walkthrough when translating freshness output into the next bounded read operation. The JSON retains only fields needed for the decision.

## 1. Check freshness

```bash
python skills/engineering/map-codebase/scripts/cli.py status \
  --repo-root . --format json
```

```json
{
  "status": "partially-stale",
  "reason": "2 repository changes.",
  "changed_files": [
    "skills/engineering/map-codebase/SKILL.md",
    "skills/engineering/map-codebase/scripts/resolve_task.py"
  ],
  "requires_full_rebuild": false,
  "repository_metadata_changed": true,
  "detection_mode": "git-diff"
}
```

`partially-stale` supplies a safe delta, so refresh those paths rather than rebuilding everything.

## 2. Refresh the reported delta

```bash
python skills/engineering/map-codebase/scripts/cli.py refresh \
  --repo-root . \
  --changed-file skills/engineering/map-codebase/SKILL.md \
  --changed-file skills/engineering/map-codebase/scripts/resolve_task.py
```

## 3. Resolve phase 1

```bash
python skills/engineering/map-codebase/scripts/cli.py resolve \
  "Fix task ownership classification in classify_task_intent, not its callers" \
  --repo-root . --phase 1 --format json
```

```json
{
  "task": "Fix task ownership classification in classify_task_intent, not its callers",
  "phase": 1,
  "knowledge_freshness": "fresh",
  "task_intent": {
    "primary_role": "source",
    "secondary_roles": [],
    "reasons": [
      "explicit indexed symbol matched skills/engineering/map-codebase/scripts/resolve_task.py"
    ]
  },
  "status": "resolved",
  "primary_owner": {
    "path": "skills/engineering/map-codebase/scripts/resolve_task.py",
    "symbol": "classify_task_intent",
    "role": "source",
    "question": "Does classify_task_intent own the requested behavior?"
  },
  "co_owners": [],
  "alternatives": [],
  "confidence": {
    "level": "high",
    "probability": 0.98,
    "reasons": [
      "exact symbol matched classify_task_intent",
      "top candidate exceeds the configured confidence margin"
    ],
    "uncertainties": []
  },
  "targets": [
    {
      "path": "skills/engineering/map-codebase/scripts/resolve_task.py",
      "symbol": "classify_task_intent",
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

Read the returned symbol from authoritative source. Stop after its ownership and contract are verified unless an expansion trigger applies.
