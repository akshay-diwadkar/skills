# Benchmark Methodology

## Evidence boundary

The Tier B feature-flag and Tier C subscription repositories are synthetic,
seeded, and byte-reproducible. They contain domain-shaped source, tests,
configuration, schemas, migrations, generated clients, stale documentation,
legacy surfaces, and operational decoys. This makes the comparison reviewable
and repeatable; it does not establish live-agent or live-model generalization.

Tier A repositories remain smoke regressions. `realistic-large` remains at its
existing path as Tier D homogeneous-scale evidence: 206 of its 228 files use a
numbered pattern, so it is excluded from utility claims.

## Fair conditions

Every condition receives identical task text and repository state.

- Resolver-first receives ranked phase targets, emitted fallback searches, and
  only source ranges supplied by the resolver.
- Ripgrep uses an independent lexical rank over `git ls-files` and `rg`, path
  and role heuristics, and the top three complete files. It does not import the
  resolver index or scoring helpers.
- Broad inventory receives tracked eligible source, test, and configuration
  inventory and complete eligible content where appropriate.

Prompts and answers live outside fixture repositories. Owner claims are bound
to file SHA-256 values and symbols. Executable oracle tests are copied into a
temporary repository only after materialization. Network access is not needed.

## Metrics and gates

The report records Hit@1, Hit@3, MRR, role precision/recall/F1, set-level owner
precision/recall, abstention precision/recall, incorrect high-confidence
targets, exact bytes and characters, offline `cl100k_base` tokens, patch
success, tokens per successful patch, failed-attempt tokens, and stable latency
budget outcomes. Incorrect resolutions receive no credited efficiency saving.

Version-1 utility gates are:

- new-case Hit@1 at least 0.75, Hit@3 at least 0.90, MRR at least 0.82;
- macro role F1 at least 0.75;
- abstention precision and recall at least 0.80;
- no incorrect high-confidence target;
- resolver patch success non-inferior to both baselines;
- at least one strict paired win: 10 percentage points of Hit@1, 15 points of
  secondary-owner F1, or 30% fewer tokens per successful patch;
- equal patch success versus inventory with at least 80% fewer tokens;
- phase-one p95 under two seconds, build median under 30 seconds, and refresh
  median under 15 seconds.

The legacy smoke gate is evaluated per repository against the committed
baseline and may not regress.

## Patch simulations

Six canonical transforms are selected solely from the context supplied by each
condition. The harness then runs injected behavioral tests, checks changed
paths, and verifies protected paths. These are context-sufficiency simulations,
not model-performance evidence.

## Limitations

Synthetic repositories omit social, organizational, and runtime context found
in production systems. Deterministic transforms do not model code generation.
Raw latency varies by machine, so raw samples are optional local output; only
sample counts and budget outcomes are committed. The other skill portfolios
have not yet received fair baselines and outcome-specific comparative oracles.
