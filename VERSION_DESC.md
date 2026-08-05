# plan-change 5.0.0 / implement-plan 3.3.0: plan-contract v7 completeness

`plan-change` 5.0.0 emits plan-contract v7. Plans now require Obligations (`RQ`) records that bind exact request/handoff anchors to success criteria and implementation or verification ownership, every `CH` declares `depends_on`/`locality`/`reversibility`, shared changes require propagation accounting, and intents include `migration` and `operational`. Sealing stays one-pass, agent-first, and read-only over cited files. `implement-plan` 3.3.0 consumes v7 topo-ordered change graphs under implementation-contract v4 while retaining a frozen reader for historical sealed v6 plans. Offline provider-free quality fixtures validate complete vs incomplete plans separately from the sealing microbenchmark.

Upstream handoff skills patch for selected-region obligation binding notes: `audit-codebase` 4.1.2, `design-codebase` 3.0.2, `optimize-codebase` 4.0.2, and `scope-issue` 4.0.2.
