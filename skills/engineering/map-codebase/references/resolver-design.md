# Deterministic Resolver Design

Use this reference when changing ownership classification, candidate evidence, scoring, confidence, symbol focusing, or phase construction.

## Pipeline

```text
task
  -> structured positive/negative query parsing
  -> ownership, component, subsystem, and cardinality intent
  -> IDF-weighted lexical shortlist
  -> symbol-centric ranking
  -> capped relationship evidence
  -> calibrated owner selection
  -> bounded read phases
```

### 1. Structured query parsing

The resolver extracts explicit paths and symbols plus positive and excluded concepts. Contrastive spans introduced by `not`, `rather than`, `instead of`, and `exclude` may exclude roles, subsystems, component types, or concepts. It also records requested architectural layer, phase intent, and whether co-ownership was explicitly requested.

### 2. Ownership classification

Ownership role remains `source`, `test`, or `configuration`. Exact indexed paths and symbols decide first. Otherwise the deterministic role table classifies task phrasing. Source owns mixed implementation tasks, while directly requested test maintenance and configuration work retain their roles.

### 3. Candidate scoring

Path, filename, normalized subsystem path, component type, symbol, synonym, configuration-key, generated, vendor, and freshness evidence produces the initial shortlist. Corpus IDF and file-length normalization reduce generic-name collisions. Evidence families are capped.

### 4. Symbol-centric ranking

Shortlisted symbols are ranked from qualified name, signature, type hints, docstring, decorators, implemented interfaces, references, calls, constants/configuration use, and control-flow markers. A file score is led by its best symbol; secondary symbols and file-level evidence are capped.

### 5. Relationship and decoy controls

Relationships never create an ownership candidate and share a small evidence cap. Generated, migration, documentation, and legacy candidates are penalized unless explicitly requested. Negative conflicts can force ambiguity or abstention.

### 6. Confidence

Confidence returns `resolved`, `ambiguous`, or `abstain`, plus a normalized probability and legacy level/raw score. Inputs include direct score, margin, evidence diversity, exact path/symbol evidence, component and subsystem matches, freshness, focus, and negative conflicts. A unique focused exact symbol is eligible for high confidence.

### 7. Result cardinality and phases

- `primary_owner` is the single default owner.
- `co_owners` require an explicit multi-owner query and independent direct evidence.
- `alternatives` preserve bounded retrieval recall without being presented as owners.
- `constraints` and `impacts` belong to phases 2 and 3.
- `targets` remains the compatibility projection of the requested phase.

Each phase includes a question, stop condition, and expansion triggers. `--phase all` remains for debugging and human inspection.
