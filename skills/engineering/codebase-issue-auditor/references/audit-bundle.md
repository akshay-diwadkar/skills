# Audit Bundle Contract

Use UTF-8 JSON with `schema_version: 1`. Validate it with `scripts/validate_audit_bundle.py` before presenting issue drafts. The validator is the executable source of truth; this file explains the authoring contract.

## Top-level fields

- `schema_version`: integer `1`.
- `audit_context`: target, commit, dirty state, selected categories, severity threshold, output mode, exclusions, and limitations.
- `repository_inventory`: purpose, runtimes, boundaries, generated/vendor paths, baseline command results, subsystems, and externally exposed or destructive workflows.
- `risk_surfaces`: risk-weighted behaviors with locations, validation actions, terminal status, and candidate/reject links.
- `coverage`: exactly one record for every selected category in every subsystem.
- `deep_analysis`: exactly one investigation record for each discovery pattern, using `not-applicable` with a concrete conclusion when the repository has no plausible target.
- `candidates`: every investigated root-cause candidate with evidence and a terminal decision.
- `rejects`: decision records for candidates marked `rejected`, `deferred`, or `merged`.
- `issues`: one structured draft link for every accepted candidate.

## Enumerations

- Categories: `bug`, `security`, `performance`, `test-gap`, `architecture`, `maintainability`, `developer-experience`.
- Severities: `critical`, `high`, `medium`, `low`.
- Confidence: `high`, `medium`, `low`.
- Candidate decisions: `accepted`, `rejected`, `deferred`, `merged`.
- Risk-surface status: `accepted`, `clean`, `rejected`, `deferred`.
- Coverage status: `complete`, `not-applicable`, `deferred`.
- Reproduction status: `reproduced`, `reasoned`, `not-run`.

## Required object shapes

```json
{
  "schema_version": 1,
  "audit_context": {
    "target": "/repo",
    "commit": "abc123",
    "dirty_worktree": false,
    "categories": ["bug", "security"],
    "severity_threshold": "medium",
    "output_mode": "github-draft",
    "scope_exclusions": [],
    "limitations": []
  },
  "repository_inventory": {
    "purpose": "Service purpose",
    "runtimes": ["Python 3.11"],
    "boundaries": ["app/"],
    "generated_or_vendor_paths": [],
    "baseline_commands": [
      {"command": "pytest", "status": "passed", "evidence": "12 passed"}
    ],
    "subsystems": [
      {"id": "api", "name": "HTTP API", "paths": ["app/api.py"], "risk_level": "high"}
    ],
    "exposed_or_destructive_workflows": ["DELETE /accounts/{id}"]
  },
  "risk_surfaces": [
    {
      "id": "account-delete",
      "title": "Account deletion",
      "risk_level": "critical",
      "categories": ["security", "bug"],
      "locations": ["app/api.py:40"],
      "validation_actions": ["Traced authorization and deletion call"],
      "status": "accepted",
      "candidate_ids": ["C-001"],
      "reject_ids": [],
      "conclusion": "Authorization is not enforced before deletion."
    }
  ],
  "coverage": [
    {
      "id": "api-security",
      "subsystem_id": "api",
      "category": "security",
      "status": "complete",
      "locations": ["app/api.py"],
      "methods": ["Traced every mutating route to its authorization guard"],
      "candidate_ids": ["C-001"],
      "reject_ids": [],
      "conclusion": "One authorization defect accepted."
    }
  ],
  "deep_analysis": [
    {
      "pattern": "default-value-trap",
      "status": "complete",
      "targets": ["app/jobs.py:18"],
      "methods": ["Traced legitimate falsy inputs across the request boundary"],
      "candidate_ids": ["C-001"],
      "reject_ids": [],
      "conclusion": "An explicit zero is replaced by the default."
    }
  ],
  "candidates": [
    {
      "id": "C-001",
      "title": "Require authorization before deleting accounts",
      "summary": "The deletion route reaches the store without an authorization decision.",
      "category": "security",
      "severity": "high",
      "confidence": "high",
      "root_cause": "The route omits the authorization middleware used by other mutations.",
      "affected_workflow": "Account administration",
      "impact": "An unauthenticated caller can permanently remove another account.",
      "evidence": [
        {"kind": "source", "location": "app/api.py:40", "observation": "Calls delete directly."},
        {"kind": "source", "location": "app/auth.py:12", "observation": "Guard exists but is not applied."}
      ],
      "reproduction": {"status": "reasoned", "details": "Unauthenticated route reaches delete.", "justification": ""},
      "counter_evidence_checked": ["Checked global middleware and store-level authorization."],
      "verification": ["Add a regression test proving an unauthenticated request returns 401."],
      "acceptance_criteria": ["Deletion requires the documented authorization policy."],
      "independently_fixable": true,
      "decision": "accepted",
      "merged_into": ""
    }
  ],
  "rejects": [],
  "issues": [
    {"candidate_id": "C-001", "title": "Require authorization before deleting accounts", "labels": ["audit", "security"]}
  ]
}
```

Add the remaining subsystem/category coverage and all 12 deep-analysis records. `not-run`, `not-applicable`, `deferred`, and `merged` records require a concrete explanation. High/critical deferred surfaces must also appear in `audit_context.limitations`.

## Legacy issue input

The publisher also accepts an issue array or `{ "issues": [...] }` where each issue contains `title`, `body`, `labels`, `severity`, `category`, `evidence`, and `acceptance_criteria`. Legacy inputs are publishable but do not establish repository coverage.
