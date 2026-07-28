# Deterministic Resolver Design

Use this reference when changing ownership classification, candidate evidence, scoring, confidence, symbol focusing, or phase construction.

## Pipeline

```text
task
  -> signal extraction
  -> ownership classification
  -> lexical candidates
  -> relationship reranking
  -> symbol/range focusing
  -> confidence
  -> bounded read phases
```

### 1. Signal extraction

The resolver extracts explicit paths, explicit symbols, literal terms, stemmed forms, and configured synonyms. Protected compounds such as `JavaScript`, `TypeScript`, and `sign in` are normalized before camel-case and punctuation splitting.

### 2. Ownership classification

Ownership is one of `source`, `test`, or `configuration`. Exact indexed paths and symbols decide first. Otherwise a deterministic scored rule table classifies task phrasing. Source owns mixed implementation tasks, while directly requested test maintenance and configuration work retain their own roles.

### 3. Lexical candidates

Indexed path, filename, subsystem, symbol, synonym, configuration-key, generated, vendor, and freshness evidence produces an initial shortlist. Every contribution uses the weights in `knowledge.config.DEFAULT_CONFIG`; the design has no second hard-coded scoring table.

### 4. Relationship reranking

Only direct indexed neighbors may expand the shortlist. Directional test links, imports, reverse imports, and entry-point evidence adjust scores. Vendor, generated, unsupported-extractor, and stale-knowledge penalties remain explicit evidence.

### 5. Symbol and range focusing

The resolver loads only symbol shards needed by shortlisted paths. Exact or expanded task terms focus source targets to matching symbols. Configuration targets instead rank active structural keys and return bounded TOML, INI, YAML, JSON, or Make ranges.

### 6. Confidence

No target yields low confidence. A positive target normally yields medium confidence. High confidence additionally requires fresh knowledge, a focused range, configured score separation, multiple positive evidence families, and a unique exact path, exact symbol, or non-weak filename signal. Synonym or relationship evidence alone cannot produce high confidence.

### 7. Bounded read phases

Phase 1 returns likely primary owners. Phase 2 returns direct tests or explicitly represented secondary configuration/test constraints. Phase 3 returns directional one-hop impacts. Consumers request phase 2 or 3 only when the preceding phase exposes an expansion trigger; confidence does not automatically expand the response.

Each phase includes its question, stop condition, and expansion triggers. `--phase all` exists for debugging and human inspection rather than normal agent navigation.
