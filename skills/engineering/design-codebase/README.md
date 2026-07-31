# Design-to-Plan Pipeline

`plan-change` is the common planning stage for two upstream workflows:

```text
GitHub issue -> scope-issue -> issue-derived request/plan ----\
                                                              -> plan-change
Repository design pressure -> design-codebase -> handoff.md --/
```

Both upstream artifacts are passed to:

```bash
python /absolute/plan-change/scripts/prepare_plan.py \
  --repo-root /absolute/path/to/repository \
  --request-file /absolute/path/to/upstream-artifact.md \
  --run-dir /absolute/path/to/temporary-run \
  --tier <tiny|standard|high-risk> \
  --intent <feature|bug-fix|refactor> \
  --anchor <repository/path[:symbol]>
```

Use `scope-issue` when an issue must be reconciled with the checkout before
planning. Use `design-codebase` when ownership, boundary, or abstraction must
be decided first. A finalized design handoff retains its eight design sections
and carries SHA-256 bindings for every local evidence range. Structural choices
also state coupling direction and cite repository evidence; other vocabulary is
used only when it improves the decision.

## `request_sha256`

`prepare_plan.py` reads the request as UTF-8 text and stores
`sha256(request.encode("utf-8")).hexdigest()` as `request_sha256` in
`inventory.json`. This fingerprints the exact request text consumed while
building that inventory. A consumer can later recompute and compare it to
detect different request text.

The fingerprint does not authenticate the request or its author, verify cited
evidence freshness, bind the request to a checkout or Git commit, or prove that
the generated inventory or plan is correct and complete. It provides no
automatic later-change detection unless a consumer explicitly recomputes and
compares it.

See [plan-change](../plan-change/README.md) and
[scope-issue](../scope-issue/README.md).
