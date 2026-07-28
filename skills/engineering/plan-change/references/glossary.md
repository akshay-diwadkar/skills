# Plan-contract v5 glossary

Read each row as an ownership rule: a record exists to prove, decide, change, or
verify something specific. `n` is a positive integer unique within that record
family.

## Record families

| Form | Plain-English meaning |
|---|---|
| `SC-n` | Success criterion: one observable given/when/then outcome plus behavior that must remain unchanged. |
| `F-n` | Fact: current repository evidence bound to an exact path, line range, anchor, excerpt hash, and file hash. |
| `D-n` | Decision: the selected approach, its evidence, the rejected alternative, and the selected approach's drawback. |
| `C-n` | Constraint: a non-negotiable implementation or acceptance limit, grounded by `F-n` when it comes from the repository. |
| `CH-n` | Change: one owned file/anchor edit with locality, reversibility, evidence, and literal implementation behavior. |
| `P-n` | Propagation disposition: how one material caller, consumer, re-export, fixture, generator, configuration, schema, deployment hook, or documentation surface is handled. |
| `B-n` | Boundary trace: a concrete three-stage flow from an input or shared boundary through grounded code to an observable result. |
| `O-n` | Domain obligation: proof that one required risk-domain concern is satisfied, or grounded proof that it is not applicable. |
| `R-n` | Risk: a concrete high-risk failure mode owned by changes and verification. |
| `T-n` | Test: exact setup, action, observable expectation, and runnable command. |
| `A-name` | Adversarial attack: a required failure-mode review that is either repaired or dismissed with attack-specific evidence. |
| `X-n` | Domain dismissal: grounded evidence and a concrete reason for removing a provisional risk domain from final classification. |

Traceability rows map every `SC-n`/`C-n` to owning `CH-n` and `T-n` records.
An execution blueprint is the literal branch, error, ordering, side-effect, and
compatibility design for one or more `CH-n`; standard and high-risk plans require
one, and high-risk blueprint domains must exactly cover final risk domains.

## Record field templates

Use fields in this order. A field marked optional is permitted by the contract
but has no unconditional or validator-defined conditional requirement.

```text
SC-n: given: <setup> (required) | when: <action> (required) | then: <observable outcome> (required) | unchanged: <preserved behavior> (required)
F-n: kind: <kind> (required) | path: <repository path> (required) | lines: <start>-<end> (required) | anchor: <exact anchor> (required) | excerpt-sha256: <hash> (required) | file-sha256: <hash> (required) | observation: <current fact> (required) | parameters: <exact parameters> (required if kind is function-signature) | returns: <exact return> (required if kind is function-signature) | async: <true|false> (required if kind is function-signature) | bases: <exact bases> (required if kind is class-signature) | fields: <exact fields> (required if kind is schema-shape) | key: <config key> (required if kind is config-key) | value: <config value> (required if kind is config-key) | condition: <exact condition> (required if kind is branch) | error: <exact error> (required if kind is error) | effect: <exact effect> (required if kind is side-effect) | caller: <qualified caller> (required if kind is call-edge) | callee: <qualified callee> (required if kind is call-edge or external-call) | generator: <generator path or anchor> (required if kind is generated-from) | output: <generated output> (required if kind is generated-from) | directory: <owned directory> (required if kind is directory-ownership)
D-n: selected: <chosen approach> (required) | evidence: <F-n|C-n references> (required) | rejected: <rejected alternative> (required) | drawback: <selected approach drawback> (required)
C-n: constraint: <non-negotiable limit> (required) | evidence: <F-n references> (optional)
CH-n: path: <repository path> (required) | anchor: <exact anchor> (required) | status: <existing|new> (required) | locality: <local-production|shared-production|test-only> (required) | reversibility: <reversible|conditional|irreversible> (required) | evidence: <F-n references> (required) | change: <literal implementation behavior> (required) | directory-owner: <CH-n|F-n references> (one of directory-owner or generator-owner required if status is new) | generator-owner: <CH-n|F-n references> (one of directory-owner or generator-owner required if status is new)
P-n: owner: <CH-n references> (required) | because: <F-n references> (required) | surface: <material surface> (required) | disposition: <changed|test-only|generated|unchanged|out-of-scope> (required)
B-n: class: <concrete boundary class> (required) | path: <F-n references> (required) | flow: <stage one -> stage two -> stage three> (required)
O-n: domain: <final risk domain> (required) | obligation: <domain obligation> (required) | status: <satisfied|not-applicable> (required) | coverage: <obligation-specific coverage> (required) | evidence: <F-n references> (required) | decision: <D-n references> (required if status is satisfied) | changes: <CH-n references> (required if status is satisfied) | tests: <T-n references> (required if status is satisfied) | reason: <grounded absence reason> (required if status is not-applicable; forbidden if satisfied)
R-n: severity: <severity> (required) | owner: <CH-n references> (required) | tests: <T-n references> (required) | risk: <concrete failure mode> (required)
T-n: given: <setup> (required) | when: <action> (required) | then: <observable expectation> (required) | command: <runnable command> (required)
A-name: status: <repaired|dismissed|not-applicable> (required) | finding: <attack-specific finding> (required) | evidence: <F-n references> (required) | resolution: <CH-n|T-n|F-n|D-n references> (required) | reason: <attack-specific dismissal reason> (required if status is dismissed or not-applicable; forbidden if repaired)
X-n: domain: <provisional risk domain> (required) | status: dismissed (required) | evidence: <F-n references> (required) | reason: <grounded dismissal reason> (required)
```

## Classification fields

| Term or value | Plain-English meaning |
|---|---|
| `provisional` | Classification chosen before grounding; final classification may stay equal or become safer, never downgrade. |
| `final` | Classification justified after grounding and used by validation. |
| `intent` | Requested change class: `feature`, `bug-fix`, or `refactor`. |
| `tier` | Planning rigor: `tiny`, `standard`, or `high-risk`. |
| `risk_domains` | Material public-contract, durable-state, migration, security, concurrency, external-integration, or irreversible-effect concerns. |
| `tier_signals` | Typed reasons that force at least `standard`; use every signal found in provisional and final metadata. |
| `transitive-consumers` | Behavior reaches consumers beyond direct callers. |
| `shared-internal-interface` | Multiple repository areas depend on a non-public shared interface. |
| `uncertain-root-cause` | Evidence does not yet support one definite deepest cause. |
| `multiple-architectural-layers` | The change crosses distinct layers such as route, service, and persistence. |
| `mixed-sync-async-consumers` | Both synchronous and asynchronous consumers depend on the behavior. |
| `multiple-test-surfaces` | More than one distinct test surface must change or verify the result. |

## Propagation and change values

Every `P-n` always names an owning `CH-n` in `owner` and grounded `F-n` in
`because`; its disposition explains what that owner does with the surface.

| Field value | Plain-English meaning |
|---|---|
| `changed` | The propagation surface changes and its `owner` names the responsible `CH-n`. |
| `test-only` | Only test code changes and its `owner` names the responsible `CH-n`. |
| `generated` | The owning `CH-n` changes the authoritative generator, while `F-n` proves the output relationship; never hand-edit generated output. |
| `unchanged` | The owning change preserves the surface for the grounded reason in `because: F-n`. |
| `out-of-scope` | The owning change intentionally excludes the surface for the grounded reason in `because: F-n`, not merely as a deferral. |
| `local-production` | Production behavior is confined to one local implementation area. |
| `shared-production` | Production behavior or an interface is shared by multiple consumers or areas. |
| `test-only` locality | The `CH-n` edits only tests or test support. |
| `reversible` | The edit can be safely reverted without migration, compensation, or lost work. |
| `conditional` | Reversal is safe only under named state, ordering, or rollout conditions. |
| `irreversible` | Reversal cannot undo a durable or external effect; compensation or roll-forward is required. |
| `existing` change status | The `CH-n` edits a path and anchor that already exist and are grounded by same-path `F-n`. |
| `new` change status | The `CH-n` creates an absent path and cites semantic directory or generator ownership. |
| `satisfied` obligation status | `O-n` owns evidence, decision, changes, and concept-specific tests. |
| `not-applicable` obligation status | `O-n` cites evidence and a concrete absence reason, with no decision/change/test ownership. |
| `repaired` attack status | `A-name` found a concrete weakness repaired by relevant `CH-n` and `T-n`. |
| `dismissed` attack status | `A-name` or `X-n` is excluded only with specific grounded evidence and reason. |
