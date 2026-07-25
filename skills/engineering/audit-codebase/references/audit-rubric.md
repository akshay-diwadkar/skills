# Audit Rubric

Use this file as the single source of truth for promoting candidates. Discovery patterns identify signals; this rubric decides whether they become issues.

## Universal promotion gate

Accept a candidate only when all conditions hold:

- **Root cause:** identify the implementation, configuration, dependency, or workflow cause rather than a symptom.
- **Affected workflow:** name the user, operator, maintainer, build, test, or runtime path harmed by the cause.
- **Impact:** state the concrete incorrect outcome, exposure, cost, or change risk for that workflow.
- **Evidence chain:** provide at least two concrete observations, including local source, config, test, command, or history evidence. External evidence cannot stand alone.
- **Reproduction:** record a reproduced result, a complete reasoned failure path, or why direct reproduction is unsafe or inapplicable.
- **Disconfirmation:** inspect credible alternative explanations, guards, reachability, framework guarantees, and intentional-design evidence.
- **Verification:** give commands, tests, or manual checks that would prove the root cause is removed.
- **Acceptance:** provide observable, independently testable closure criteria.
- **Actionability:** keep one independently fixable root cause per candidate.
- **Threshold:** require high confidence and severity at or above the configured threshold; default to `medium+`.

Reject guesses about hidden production state, unobserved user behavior, or product intent unless local code provides a complete credible failure path.

## Confidence

- `high`: direct code/config evidence plus reproduction, test/command evidence, authoritative metadata, or a complete reasoned path that survives disconfirmation.
- `medium`: credible signal with one material confirmation missing. Preserve it as a near-miss; do not draft by default.
- `low`: speculation or pattern matching without a concrete failure path. Reject it.

Ecosystem candidates also require current primary-source documentation, release notes, registry metadata, or an advisory that applies to the locally observed version/configuration.

## Severity

- `critical`: likely data loss, security exposure, production outage, broken release path, or a defect blocking most users.
- `high`: credible user-visible failure, significant security/performance risk, or blocker for important work.
- `medium`: concrete correctness, coverage, maintainability, architecture, or workflow issue that should be scheduled.
- `low`: limited-risk cleanup or optimization; exclude by default.

## Category assignment

Choose the category that best represents impact, not the discovery technique:

- `bug`: wrong behavior, crash, data loss, or violated contract;
- `security`: auth/authz, injection, secrets, unsafe parsing, vulnerable dependency, or sensitive-data risk;
- `performance`: measurable or structurally unavoidable excess work or scaling risk;
- `test-gap`: important behavior or integration lacks meaningful automated coverage;
- `architecture`: boundaries or dependencies create concrete broad-change or ownership risk;
- `maintainability`: duplication, dead code, fragile configuration, or unclear error/compatibility ownership increases defect risk;
- `developer-experience`: setup, scripts, CI feedback, or diagnostics make normal development error-prone or materially slower.

## Cross-cutting and ecosystem findings

For a deep-analysis candidate, require evidence from at least two files or distinct system boundaries. The second location must participate in the failure chain, not merely mention the same symbol.

For an ecosystem candidate, require all of:

- local evidence of the exact version, configuration, or usage;
- current primary-source evidence for the claimed capability, default, advisory, or migration;
- a concrete expected benefit and verification path;
- an independently actionable change, not “upgrade because newer exists.”

## False-positive rejects

Reject when an explicit guard or documented rationale makes the behavior intentional, the path is unreachable, a framework guarantee prevents the failure, evidence exists only in generated/vendor/test-only code without production impact, or the signal duplicates another root cause.
