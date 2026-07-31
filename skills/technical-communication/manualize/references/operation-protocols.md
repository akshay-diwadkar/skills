# Operation Protocols

## Write

1. Identify document type, audience, risk, profile, output directory, and
   authoritative local sources. Complete when every technical claim has a source
   or an unresolved-gap label.
2. Create `manual-bundle.json` from `templates/manual-bundle.json`. Bind source
   hashes, canonical claims, exact commands, paths, values, ordering,
   prerequisites, branches, warnings, and recovery.
3. Define preferred terms, forbidden variants, abbreviations, action verbs,
   phrasal verbs, and hazardous actions in the glossary.
4. Draft from `templates/manual.md`. Put conditions before actions and warnings
   before hazards; preserve bound literals exactly.
5. Run `check_manual_language.py` and `check_manual.py` until neither emits an
   error, then run `finalize_manual.py`.

Do not finalize while a source gap or validator error remains.

## Audit

1. Hash the manual, bundle, glossary, and bound sources before analysis. Create
   or load a bundle with `operation: audit`; never pass it to the finalizer.
2. Run the language and semantic validators without changing any input.
3. Render `templates/manual-audit.md` and `templates/manual-audit.json` in a
   separate output directory and include every diagnostic.
4. Hash every input again and record before/after hashes in both reports.

If any input hash changed, report audit-integrity failure. Audit does not grant
remediation authority.
