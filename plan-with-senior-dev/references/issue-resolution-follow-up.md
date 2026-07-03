# Issue Resolution Follow-Up

Use this branch for GitHub issue fixes, audit-finding fixes, and repo-fix plans likely to resolve tracked issues.

Add a `Post-Resolution Audit Follow-Up` section after normal implementation and verification. The section must tell the implementer to:

1. Rerun `codebase-issue-auditor` against the local repo after all planned fixes and tests pass.
2. Compare current audit findings against open audit or GitHub issues.
3. List resolved issue candidates with source, test, or audit evidence showing the finding no longer reproduces.
4. Close resolved issues only after explicit user approval.

If GitHub credentials or the repository URL are missing, keep the close candidates as a local report and do not attempt external issue closure.
