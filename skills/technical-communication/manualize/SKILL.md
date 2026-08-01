---
name: manualize
description: Write or audit source-grounded technical manuals, procedures, runbooks, guides, notices, error messages, and reference documentation. Use when technical content must preserve supplied facts while following deterministic controlled-language and operational-completeness checks.
version: 3.0.0
metadata:
  invocation: both
disable-model-invocation: false
user-invocable: true
---

# Manualize

## Purpose and authority

Use MTE-1 to make supplied technical information explicit, executable, and
traceable. MTE-1 is original and only inspired by ASD-STE100: never claim
official ASD-STE100 compliance or imply that this skill contains its
approved-word dictionary. Validation does not establish independent factual truth.

Use `operation: write` only with document-creation or revision authority. Use
`operation: audit` for read-only inspection; implicit invocation never grants
write or remediation authority. Use `profile: strict` for hazardous procedures,
commands, warnings, notices, and recovery; otherwise use `profile: standard`.

## Start

Resolve `skill-root` to this directory, keep artifacts outside it, and pass
absolute paths:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --run-dir /absolute/run --input request_file=/absolute/request.md \
  --input operation=audit --input profile=standard \
  --input manual=/absolute/manual.md --input bundle=/absolute/bundle.json \
  --input glossary=/absolute/glossary.json --format json doctor
```

Run each returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`. Apply deterministic operation/profile classification unless
the supported hash-bound contrary-evidence artifact proves an override.

## Next-step loop

Read [MTE-1](references/mte-1.md) for language rules and
[Manual Bundle](references/manual-bundle.md) for artifact shape. Follow the
matching branch in [Operation Protocols](references/operation-protocols.md).
During writing, use [Source Grounding](references/source-grounding.md). During
audit, interpret every diagnostic with [Audit Report](references/audit-report.md).

Never invent source facts. Preserve bound commands, paths, values, ordering,
warnings, and recovery. Audit must not modify the manual, bundle, glossary, or
bound sources.

## Completion and recovery

Write completes only at phase `complete` with `status: final`, a validation
receipt, `manual.md`, and `manual-bundle.json`. Audit completes only with
`manual-audit.md` and `manual-audit.json` covering every rule and semantic error
and matching before/after hashes that prove read-only behavior.

Repair only the artifact allowed by the current phase. If evidence is missing,
record an unresolved gap; if audit hashes change, report audit-integrity failure
and do not present remediation as complete.
