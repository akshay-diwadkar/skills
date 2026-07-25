# Deterministic Resolver Pipeline Design

The resolver operates in 7 distinct deterministic stages without relying on LLM hallucination for candidate path selection.

## Pipeline Stages

```
[Task String] ──> [A: Signal Extractor] ──> [B: Intent Classifier]
                                                     │
                                                     ▼
[Read Plan] <── [G: Read Plan] <── [F: Expansion] <── [C: Candidates] ──> [D: Scorer] ──> [E: Confidence]
```

### Stage A: Signal Extraction
Extracts exact paths, symbols, filenames, error strings, domain nouns, and action verbs from natural language task input.

### Stage B: Intent Classification
Identifies task categories (`feature`, `bug`, `refactor`, `security`, `test`, `config`, `migration`, etc.) to adjust scoring weights dynamically.

### Stage C: Candidate Generation
Uses lexical indexing, AST symbols, imports, source-test mapping, entry-point links, and config references to build candidate set. Excludes vendor/generated code.

### Stage D: Explainable Scoring
Computes score per candidate using weighted evidence:
`score = exact_symbol (10.0) + exact_path (10.0) + filename (7.0) + subsystem (5.0) + entry_point (5.0) + test_rel (4.0) + config_rel (4.0) + keyword (2.0) - vendor (-10.0) - generated (-8.0)`
Every score includes explicit reason strings.

### Stage E: Confidence Estimation
Calculates confidence (`high`, `medium`, `low`) based on signal agreement, top score margin, and index freshness.

### Stage F: Progressive Expansion
- `high`: Primary targets + direct tests + direct configs.
- `medium`: 1st-order dependencies + adjacent tests.
- `low`: Subsystem neighbors + extra entry points + targeted grep.

### Stage G: Source Read Plan
Outputs ordered step-by-step reading plan with rationale and explicit skip list.
