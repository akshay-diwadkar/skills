---
name: manualize
description: Write or audit source-grounded technical manuals, procedures, runbooks, guides, notices, error messages, and reference documentation. Use when technical content must preserve supplied facts while following deterministic controlled-language and operational-completeness checks.
version: 2.2.0
metadata:
  invocation: both
disable-model-invocation: false
user-invocable: true
---

# Manualize

Start the common CLI with `request_file`. Its deterministic result selects the
read-only/write operation and controlled-language profile; `next` applies the
selection. Ambiguous authorization stays read-only and incomplete risk evidence
uses the strict profile.

Use MTE-1 to make technical information explicit, executable, and traceable to supplied sources. MTE-1 is an original controlled-English system inspired by ASD-STE100. Never claim official ASD-STE100 compliance. This skill does not contain or reproduce the ASD-STE100 approved-word dictionary.

Use `scripts/cli.py` as the primary executable entrypoint. Select `write` to
validate and finalize through the existing authoritative scripts, or `audit`
to produce a hash-backed read-only report without invoking the finalizer.
Existing validators and finalizer commands remain supported.

Resolve `skill-root` as this directory. Run bundled scripts by absolute path, pass absolute artifact paths, and keep working files outside the installed skill. Technical correctness depends on the supplied source material; validation does not establish independent factual truth.

## Select the Operation

Use `operation: write` to create or revise a document with authorization. Use `operation: audit` to inspect an existing document. Audit is read-only unless the user explicitly authorizes remediation.

Implicit invocation never supplies write or remediation authority. If the
request does not explicitly authorize document creation, revision, or audit
remediation, select `operation: audit` and keep the source document unchanged.

Select `profile: strict` for safety-critical procedures, commands, warnings, notices, and error recovery. Select `profile: standard` for explanatory or reference content unless risk requires strict.

Read [references/mte-1.md](references/mte-1.md) before drafting or auditing. Read [references/manual-bundle.md](references/manual-bundle.md) before creating a bundle.

## Write

1. **Frame the document.** Identify the document type, audience, risk, profile, output directory, and authoritative local sources. Read [references/source-grounding.md](references/source-grounding.md). Complete this step when every technical claim has an identified source or is labeled as an unresolved gap.
2. **Bind the evidence.** Create `manual-bundle.json` from [templates/manual-bundle.json](templates/manual-bundle.json). Record source hashes, canonical claims, exact commands, paths, values, procedure order, prerequisites, branches, warnings, and recovery steps. Complete this step when the bundle schema represents every operational obligation.
3. **Control the terminology.** Define preferred terms, forbidden variants, abbreviations, action verbs, phrasal verbs, and hazardous actions in the inline glossary. Complete this step when one term has one meaning throughout the planned document.
4. **Draft the manual.** Use [templates/manual.md](templates/manual.md). Put conditions before actions and warnings before hazards. Preserve bound commands, paths, and values exactly.
5. **Validate and repair.** Run both checks until neither emits an error:

   ```bash
   python /absolute/skill-root/scripts/check_manual_language.py --profile <strict|standard> --glossary /absolute/path/to/glossary.json /absolute/path/to/manual.md
   python /absolute/skill-root/scripts/check_manual.py --repo-root /absolute/path/to/repository --bundle /absolute/path/to/manual-bundle.json /absolute/path/to/manual.md
   ```

6. **Finalize.** Run:

   ```bash
   python /absolute/skill-root/scripts/finalize_manual.py --repo-root /absolute/path/to/repository --bundle /absolute/path/to/manual-bundle.json /absolute/path/to/manual.md
   ```

Complete the operation only when the finalizer returns `status: final`, the bundle contains a validation receipt, and the final outputs are `manual.md` and `manual-bundle.json`.

## Audit

1. Hash the input manual, bundle, and bound sources before analysis. Create or load a bundle with `operation: audit`; never pass it to the finalizer.
2. Run both validators exactly as in the write operation. Do not change the manual, bundle, or sources.
3. Interpret every diagnostic with [references/audit-report.md](references/audit-report.md). Render [templates/manual-audit.md](templates/manual-audit.md) and [templates/manual-audit.json](templates/manual-audit.json) in a separate output directory.
4. Hash all inputs again. Record the before and after hashes in both audit artifacts. If any hash changed, report an audit-integrity failure and do not present remediation as completed.

Complete the operation only when the reports include every rule ID and semantic error, input hashes prove read-only behavior, and no source document was rewritten without authorization.
