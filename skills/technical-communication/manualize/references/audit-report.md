# Audit Report Interpretation

Keep audit evidence read-only. Record the SHA-256 of the manual, bundle, and every bound source before and after validation.

Group results by:

1. blocking language violations;
2. advisory language warnings;
3. source-binding failures;
4. changed commands, paths, or values;
5. procedure, warning, recovery, prerequisite, or branch gaps; and
6. limitations of the supplied sources.

Copy rule IDs and semantic error types exactly. Do not rewrite the audited manual unless the user authorizes remediation. If an input hash changes during the audit, mark the audit invalid and identify the changed artifact.
