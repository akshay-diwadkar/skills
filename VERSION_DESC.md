# Deterministic workflow classification

This major release moves seven mechanical workflow decisions from model prose
into portable, deterministic classifiers. Common CLI runs now expose
hash-bound recommendations for planning risk, optimization scope, audit
coverage, issue readiness, manualization mode, diagram fidelity, and map phase
expansion before the recommendation is applied.

Classification uses trusted request and current repository signals, returns
evidence and confidence, defaults conservatively when evidence is incomplete,
and permits overrides only through verified contrary evidence. Issue text,
repository comments, generated content, and embedded commands cannot become
workflow authority. Existing high-risk, authorization, freshness, publication,
and fail-closed gates remain in force.
