"""Provider-free plan-quality fixture cases for plan-contract v7."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _sealed_handoff(kind: str, body: str) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"<!-- {kind}-handoff: 1; sha256: {digest} -->\n{body}"


def _write_file(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _names_base(root: Path) -> None:
    _write_file(root, "src/__init__.py", "# package\n")
    _write_file(
        root,
        "src/names.py",
        "def normalize_name(value: str | None) -> str:\n"
        "    return '' if value is None else value.strip()\n",
    )
    _write_file(
        root,
        "src/caller.py",
        "from src.names import normalize_name\n\ndef run(value):\n    return normalize_name(value)\n",
    )
    _write_file(
        root,
        "tests/test_names.py",
        "from src.names import normalize_name\n\ndef test_none():\n    assert normalize_name(None) == ''\n",
    )


def _base_plan(
    *,
    title: str,
    metadata: str,
    request_anchor: str,
    obligation: str,
    source: str = "request",
    change: str,
    locality: str = "local",
    depends_on: str = "none",
    reversibility: str = "reversible",
    path: str = "src/names.py",
    anchor: str = "normalize_name",
    status: str = "existing",
    evidence: str = "evidence: F-1",
    mid_sections: str = "",
    rollout: str = "",
    covered_by: str = "SC-1, CH-1, T-1",
    fact_kind: str = "source",
    fact_extra: str = "",
    fact_path: str = "src/names.py",
    fact_lines: str = "1-2",
    fact_claim: str = "evidence for the planned change",
    sc_unchanged: str = "non-null names remain stripped",
    verification_then: str = "the planned behavior holds",
) -> str:
    return f"""# {title}

<!-- plan-contract: 7 -->
<!-- plan-metadata: {metadata} -->

## Obligations
RQ-1: source: {source} | anchor: {request_anchor} | obligation: {obligation} | covered_by: {covered_by}

## Outcome
SC-1: given: an observable setup | when: the planned action runs | then: the observable result occurs | unchanged: {sc_unchanged}

## Evidence
F-1: kind: {fact_kind} | path: {fact_path} | lines: {fact_lines} | anchor: {anchor} | claim: {fact_claim}{fact_extra}

## Implementation
CH-1: path: {path} | anchor: {anchor} | status: {status} | {evidence} | change: {change} | depends_on: {depends_on} | locality: {locality} | reversibility: {reversibility}
{mid_sections}## Verification
T-1: covers: SC-1, CH-1 | given: targeted cases | when: tests execute | then: {verification_then} | command: python -m pytest tests/test_names.py -q
{rollout}"""


@dataclass(frozen=True)
class WeakPlan:
    name: str
    expected_reason: str
    mutate: Callable[[str], str]


@dataclass(frozen=True)
class QualityCase:
    id: str
    request: str
    obligations: list[dict[str, Any]]
    build_repo: Callable[[Path], None]
    golden: str
    weak: tuple[WeakPlan, ...]
    handoff_item: str | None = None


def _manifest(
    *,
    obligation: str,
    anchor: str,
    path: str,
    claim: str,
    protected: str,
    verification: list[str],
    propagation: list[dict[str, str]] | None = None,
    risk_rollout: list[dict[str, str]] | None = None,
    dependencies: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "O1",
            "obligation": obligation,
            "anchor": anchor,
            "planned_paths": [{"path": path}],
            "owner_evidence": [
                {
                    "path": path if path.endswith((".py", ".toml", ".json")) else "src/names.py",
                    "claim": claim,
                }
            ],
            "dependencies": dependencies or [{"ch": "CH-1", "depends_on": []}],
            "propagation": propagation or [],
            "protected_behavior": [{"text": protected}],
            "risk_rollout": risk_rollout or [],
            "verification": [{"must_include": verification}],
        }
    ]


CASES: tuple[QualityCase, ...] = (
    QualityCase(
        id="tiny-local-bug",
        request="Fix absent names for normalize_name.\n",
        obligations=_manifest(
            obligation="absent input names must normalize to an empty string",
            anchor="Fix absent names",
            path="src/names.py",
            claim="root cause is absent-value handling in normalize_name",
            protected="present names remain stripped",
            verification=["fails before the fix", "passes after the fix"],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Fix absent-name normalization",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Fix absent names",
            obligation="absent input names must normalize to an empty string",
            change="return the empty string for absent values before stripping present names",
            fact_claim="root cause is absent-value handling in normalize_name",
            sc_unchanged="present names remain stripped",
            verification_then="the case fails before the fix and passes after the fix with absent input empty",
        ),
        weak=(
            WeakPlan(
                "missing-obligation",
                "section.order",
                lambda text: text.replace(
                    "## Obligations\nRQ-1: source: request | anchor: Fix absent names | obligation: absent input names must normalize to an empty string | covered_by: SC-1, CH-1, T-1\n\n",
                    "",
                ),
            ),
            WeakPlan(
                "missing-fail-before",
                "verification.regression",
                lambda text: text.replace(
                    "fails before the fix and passes after the fix",
                    "passes after the fix only",
                ),
            ),
            WeakPlan(
                "weak-protected-behavior",
                "record.invalid",
                lambda text: text.replace("unchanged: present names remain stripped", "unchanged: TBD"),
            ),
        ),
    ),
    QualityCase(
        id="shared-refactor-callers",
        request="Refactor normalize_name callers and re-export surface.\n",
        obligations=_manifest(
            obligation="refactor normalize_name callers without changing strip behavior",
            anchor="Refactor normalize_name callers",
            path="src/names.py",
            claim="normalize_name owns shared strip behavior",
            protected="strip behavior remains identical",
            verification=["caller and re-export tests pass"],
            propagation=[{"disposition": "changed", "path": "src/caller.py", "owner": "CH-1"}],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Refactor shared normalize callers",
            metadata='{"intent":"refactor","tier":"standard","risk_domains":[]}',
            request_anchor="Refactor normalize_name callers",
            obligation="refactor normalize_name callers without changing strip behavior",
            change="preserve strip behavior while clarifying the shared normalize_name owner seam",
            locality="shared",
            fact_claim="normalize_name owns shared strip behavior",
            sc_unchanged="strip behavior remains identical",
            verification_then="caller and re-export tests pass",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 caller imports the shared normalize seam
""",
        ),
        weak=(
            WeakPlan(
                "missing-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 caller imports the shared normalize seam\n",
                    "\n",
                ),
            ),
            WeakPlan(
                "bogus-propagation-path",
                "propagation.path",
                lambda text: text.replace("path: src/caller.py", "path: missing/nope.py"),
            ),
            WeakPlan(
                "token-out-of-scope",
                "propagation.evidence",
                lambda text: text.replace(
                    "disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 caller imports the shared normalize seam",
                    "disposition: out-of-scope | path: docs/none.md | owner: CH-1 | reason: not needed",
                ),
            ),
        ),
    ),
    QualityCase(
        id="feature-defaults-errors",
        request="Add default empty-name handling with clear errors.\n",
        obligations=_manifest(
            obligation="default empty-name handling with explicit errors",
            anchor="default empty-name",
            path="src/names.py",
            claim="normalize_name owns default and error paths",
            protected="valid strings remain stripped",
            verification=["defaults and errors are covered"],
            propagation=[
                {
                    "disposition": "out-of-scope",
                    "path": "src/caller.py",
                    "owner": "CH-1",
                }
            ],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Add default empty-name handling",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="default empty-name",
            obligation="default empty-name handling with explicit errors",
            change="default absent names to empty string and raise ValueError for non-string inputs before stripping",
            fact_claim="normalize_name owns default and error paths",
            sc_unchanged="valid strings remain stripped",
            verification_then="defaults and errors are covered",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: out-of-scope | path: src/caller.py | owner: CH-1 | reason: F-1 bounded sweep found no additional default owners
""",
        ),
        weak=(
            WeakPlan(
                "missing-local-declaration",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: caller | disposition: out-of-scope | path: src/caller.py | owner: CH-1 | reason: F-1 bounded sweep found no additional default owners\n",
                    "\n",
                ),
            ),
            WeakPlan(
                "missing-error-behavior",
                "change.specificity",
                lambda text: text.replace(
                    "default absent names to empty string and raise ValueError for non-string inputs before stripping",
                    "handle defaults",
                ),
            ),
        ),
    ),
    QualityCase(
        id="config-dependency-change",
        request="Raise retry_limit in settings for name sync.\n",
        obligations=_manifest(
            obligation="raise retry_limit for name sync safely",
            anchor="Raise retry_limit",
            path="config/settings.toml",
            claim="settings.toml owns retry_limit",
            protected="existing successful syncs remain valid",
            verification=["retry_limit consumers pass"],
            propagation=[{"disposition": "changed", "path": "config/settings.toml", "owner": "CH-1"}],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(root, "config/settings.toml", "retry_limit = 3\n"),
        ),
        golden=_base_plan(
            title="Raise retry_limit setting",
            metadata='{"intent":"operational","tier":"standard","risk_domains":[]}',
            request_anchor="Raise retry_limit",
            obligation="raise retry_limit for name sync safely",
            change="increase retry_limit while preserving successful sync completion semantics",
            path="config/settings.toml",
            anchor="retry_limit",
            fact_kind="config-key",
            fact_path="config/settings.toml",
            fact_lines="1-1",
            fact_extra=" | key: retry_limit | value: 3",
            fact_claim="settings.toml owns retry_limit",
            locality="shared",
            sc_unchanged="existing successful syncs remain valid",
            verification_then="retry_limit consumers pass",
            mid_sections="""
## Propagation
P-1: surface: config | disposition: changed | path: config/settings.toml | owner: CH-1 | reason: F-1 config key owns the retry surface
""",
        ),
        weak=(
            WeakPlan("missing-config-evidence", "record.invalid", lambda text: text.replace("kind: config-key", "kind: source")),
            WeakPlan(
                "missing-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: config | disposition: changed | path: config/settings.toml | owner: CH-1 | reason: F-1 config key owns the retry surface\n",
                    "\n",
                ),
            ),
        ),
    ),
    QualityCase(
        id="generated-output-ownership",
        request="Generate owned model output from tools/gen_model.py.\n",
        obligations=_manifest(
            obligation="generate owned model output from the declared generator",
            anchor="Generate owned model output",
            path="src/generated_model.py",
            claim="generator owns declared output",
            protected="handwritten names remain authoritative",
            verification=["regeneration is stable"],
            propagation=[
                {
                    "disposition": "out-of-scope",
                    "path": "src/names.py",
                    "owner": "CH-1",
                }
            ],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(
                root,
                "tools/gen_model.py",
                "OUTPUT = 'src/generated_model.py'\n\ndef generate():\n    Path = __import__('pathlib').Path\n    Path(OUTPUT).write_text('VALUE = 1\\n')\n",
            ),
        ),
        golden=_base_plan(
            title="Generate owned model output",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="Generate owned model output",
            obligation="generate owned model output from the declared generator",
            change="generate the declared model adapter from the owned generator without rewriting handwritten names",
            path="src/generated_model.py",
            anchor="OUTPUT",
            status="new",
            evidence="owner: F-1",
            fact_kind="generated-from",
            fact_path="tools/gen_model.py",
            fact_lines="1-4",
            fact_extra=" | generator: tools/gen_model.py | output: src/generated_model.py",
            fact_claim="generator owns declared output",
            sc_unchanged="handwritten names remain authoritative",
            verification_then="regeneration is stable",
            mid_sections="""
## Propagation
P-1: surface: generated | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: F-1 bounded sweep found no extra generated consumers
""",
        ),
        weak=(
            WeakPlan(
                "missing-owner",
                "change.target",
                lambda text: text.replace("status: new | owner: F-1", "status: new"),
            ),
            WeakPlan(
                "missing-local-declaration",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: generated | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: F-1 bounded sweep found no extra generated consumers\n",
                    "\n",
                ),
            ),
        ),
    ),
    QualityCase(
        id="public-contract-migration",
        request="Migrate public name schema with compatibility window.\n",
        obligations=_manifest(
            obligation="migrate public name schema with compatibility",
            anchor="Migrate public name schema",
            path="src/schema.py",
            claim="SCHEMA owns the public contract shape",
            protected="old readers keep working through the window",
            verification=["compatibility checks pass"],
            propagation=[{"disposition": "changed", "path": "src/schema.py", "owner": "CH-1"}],
            risk_rollout=[
                {"risk": "mixed-version readers could reject the new field", "rollout": "compatibility window"},
            ],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(root, "src/schema.py", "SCHEMA = {'name': 'string'}\n"),
            _write_file(root, "src/old_reader.py", "def read_old(event):\n    return event['name']\n"),
            _write_file(root, "src/new_writer.py", "def write_new(name):\n    return {'name': name}\n"),
        ),
        golden=_base_plan(
            title="Migrate public name schema",
            metadata='{"intent":"migration","tier":"high-risk","risk_domains":["public-contract","migration"]}',
            request_anchor="Migrate public name schema",
            obligation="migrate public name schema with compatibility",
            change="add the new schema field while retaining the previous name field through one compatibility window",
            path="src/schema.py",
            anchor="SCHEMA",
            fact_path="src/schema.py",
            fact_lines="1-1",
            fact_claim="SCHEMA owns the public contract shape",
            locality="shared",
            sc_unchanged="old readers keep working through the window",
            verification_then="compatibility checks pass",
            mid_sections="""
## Propagation
P-1: surface: contract | disposition: changed | path: src/schema.py | owner: CH-1 | reason: F-1 public schema owns mixed-version readers

## Boundaries and Risks
B-1: class: public schema boundary | evidence: F-1 | flow: old schema readers -> compatibility window -> new schema writers
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: mixed-version readers could reject the new field
""",
            rollout="""
## Rollout and Rollback
Deploy schema writers after readers in one compatibility window. If validation divergence appears, roll back writers and restore the previous schema snapshot.
""",
        ),
        weak=(
            WeakPlan("missing-rollout", "section.order", lambda text: text.split("\n## Rollout and Rollback", 1)[0] + "\n"),
            WeakPlan(
                "missing-risk",
                "record.invalid",
                lambda text: text.replace(
                    "\n## Boundaries and Risks\nB-1: class: public schema boundary | evidence: F-1 | flow: old schema readers -> compatibility window -> new schema writers\nR-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: mixed-version readers could reject the new field\n",
                    "\n",
                ),
            ),
        ),
    ),
    QualityCase(
        id="concurrency-idempotency",
        request="Make normalize_name idempotent under concurrent retries.\n",
        obligations=_manifest(
            obligation="idempotent normalization under concurrent retries",
            anchor="idempotent",
            path="src/names.py",
            claim="normalize_name owns concurrent retry mutation",
            protected="stripped values stay stable under retry",
            verification=["fails before the fix", "passes after the fix", "idempotent"],
            propagation=[{"disposition": "unchanged", "path": "src/caller.py", "owner": "CH-1"}],
            risk_rollout=[{"risk": "overlapping retries could mutate a value twice"}],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(
                root,
                "src/retry_state.py",
                "STATE = {'value': None}\n\ndef apply(value):\n    STATE['value'] = value\n    return STATE['value']\n",
            ),
        ),
        golden=_base_plan(
            title="Make normalization idempotent",
            metadata='{"intent":"bug-fix","tier":"high-risk","risk_domains":["concurrency"]}',
            request_anchor="idempotent",
            obligation="idempotent normalization under concurrent retries",
            change="make normalize_name idempotent so concurrent retries return the same stripped value without double mutation",
            locality="shared",
            fact_claim="normalize_name owns concurrent retry mutation",
            sc_unchanged="stripped values stay stable under retry",
            verification_then="the case fails before the fix and passes after the fix while concurrent retries stay idempotent",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: unchanged | path: src/caller.py | owner: CH-1 | reason: F-1 bounded sweep found callers already consume the idempotent result

## Boundaries and Risks
B-1: class: concurrent retry boundary | evidence: F-1 | flow: first attempt -> overlapping retry -> reconciled result
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: overlapping retries could mutate a value twice
""",
        ),
        weak=(
            WeakPlan(
                "missing-risk",
                "record.invalid",
                lambda text: text.replace(
                    "\n## Boundaries and Risks\nB-1: class: concurrent retry boundary | evidence: F-1 | flow: first attempt -> overlapping retry -> reconciled result\nR-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: overlapping retries could mutate a value twice\n",
                    "\n",
                ),
            ),
            WeakPlan(
                "missing-fail-before",
                "verification.regression",
                lambda text: text.replace("fails before the fix and passes after the fix", "passes after the fix"),
            ),
        ),
    ),
    QualityCase(
        id="external-ambiguous-success",
        request="Handle ambiguous external name sync success.\n",
        obligations=_manifest(
            obligation="handle ambiguous external sync success",
            anchor="ambiguous external",
            path="src/external_client.py",
            claim="external client owns ambiguous ack handling",
            protected="successful sync tokens remain durable",
            verification=["idempotent confirmation"],
            propagation=[{"disposition": "changed", "path": "src/external_client.py", "owner": "CH-1"}],
            risk_rollout=[
                {"risk": "ambiguous acknowledgements could double-apply sync", "rollout": "canary"},
            ],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(
                root,
                "src/external_client.py",
                "def sync_name(name):\n    return {'ack': 'maybe', 'token': None}\n",
            ),
        ),
        golden=_base_plan(
            title="Handle ambiguous external sync",
            metadata='{"intent":"feature","tier":"high-risk","risk_domains":["external-integration"]}',
            request_anchor="ambiguous external",
            obligation="handle ambiguous external sync success",
            change="treat ambiguous external sync acknowledgements as retryable until an idempotent success token is observed",
            path="src/external_client.py",
            anchor="sync_name",
            fact_path="src/external_client.py",
            fact_lines="1-2",
            fact_claim="external client owns ambiguous ack handling",
            locality="shared",
            sc_unchanged="successful sync tokens remain durable",
            verification_then="idempotent confirmation",
            mid_sections="""
## Propagation
P-1: surface: deployment | disposition: changed | path: src/external_client.py | owner: CH-1 | reason: F-1 external ack path owns the sync side effect

## Boundaries and Risks
B-1: class: external acknowledgement boundary | evidence: F-1 | flow: request sent -> ambiguous ack -> idempotent confirmation
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: ambiguous acknowledgements could double-apply sync
""",
            rollout="""
## Rollout and Rollback
Deploy behind a canary flag in order. If duplicate sync tokens appear, disable the flag and resume after compensating duplicates.
""",
        ),
        weak=(
            WeakPlan("missing-rollout", "section.order", lambda text: text.split("\n## Rollout and Rollback", 1)[0] + "\n"),
            WeakPlan(
                "token-propagation",
                "propagation.evidence",
                lambda text: text.replace(
                    "disposition: changed | path: src/external_client.py | owner: CH-1 | reason: F-1 external ack path owns the sync side effect",
                    "disposition: out-of-scope | path: docs/none.md | owner: CH-1 | reason: not needed",
                ),
            ),
        ),
    ),
    QualityCase(
        id="design-handoff-inheritance",
        request=_sealed_handoff(
            "design",
            "## Chosen Design & Depth Rationale\n"
            "- Boundary: NameGateway.normalize owns absent-name handling\n"
            "## Alternatives Considered\n"
            "### Alternative: RejectedStripOnly\n"
            "- Boundary: strip-only helper without gateway\n",
        ),
        obligations=_manifest(
            obligation="implement selected NameGateway.normalize boundary",
            anchor="NameGateway.normalize owns absent-name handling",
            path="src/names.py",
            claim="normalize_name is the chosen boundary owner",
            protected="strip behavior remains",
            verification=["selected boundary holds"],
            propagation=[{"disposition": "changed", "path": "src/caller.py", "owner": "CH-1"}],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Implement selected name gateway",
            metadata='{"intent":"refactor","tier":"standard","risk_domains":[]}',
            request_anchor="NameGateway.normalize owns absent-name handling",
            obligation="implement selected NameGateway.normalize boundary",
            source="design",
            change="introduce the selected NameGateway.normalize boundary while preserving current strip behavior",
            locality="shared",
            fact_claim="normalize_name is the chosen boundary owner",
            sc_unchanged="strip behavior remains",
            verification_then="selected boundary holds",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 callers must adopt the selected boundary
""",
        ),
        weak=(
            WeakPlan(
                "wrong-design-anchor",
                "obligation.anchor",
                lambda text: text.replace(
                    "NameGateway.normalize owns absent-name handling",
                    "strip-only helper without gateway",
                ),
            ),
            WeakPlan(
                "missing-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 callers must adopt the selected boundary\n",
                    "\n",
                ),
            ),
        ),
    ),
    QualityCase(
        id="optimization-handoff-inheritance",
        request=_sealed_handoff(
            "optimization",
            "- Selected candidate: C-1\n"
            "- H-1: next: plan-ready | candidate: C-1 | measure: p95 latency\n"
            "- C-1: cache normalize_name for repeated inputs\n"
            "- C-9: rejected speculative rewrite\n",
        ),
        obligations=_manifest(
            obligation="cache normalize_name for the selected workflow measure",
            anchor="cache normalize_name for repeated inputs",
            path="src/names.py",
            claim="normalize_name owns the measured hot path",
            protected="empty-string behavior remains",
            verification=["p95 measure improves"],
            propagation=[
                {
                    "disposition": "out-of-scope",
                    "path": "src/caller.py",
                    "owner": "CH-1",
                }
            ],
        ),
        build_repo=lambda root: (
            _names_base(root),
            _write_file(root, "bench/measure_normalize.py", "def p95(samples):\n    return sorted(samples)[int(0.95 * len(samples))]\n"),
        ),
        golden=_base_plan(
            title="Cache normalize_name path",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="cache normalize_name for repeated inputs",
            obligation="cache normalize_name for the selected workflow measure",
            source="optimization",
            change="cache normalize_name results for repeated identical inputs while preserving empty-string behavior",
            fact_claim="normalize_name owns the measured hot path",
            sc_unchanged="empty-string behavior remains",
            verification_then="p95 measure improves",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: out-of-scope | path: src/caller.py | owner: CH-1 | reason: F-1 bounded sweep found no extra measure owners beyond the hot path
""",
        ),
        weak=(
            WeakPlan(
                "wrong-candidate-anchor",
                "obligation.anchor",
                lambda text: text.replace(
                    "cache normalize_name for repeated inputs",
                    "rejected speculative rewrite",
                ),
            ),
            WeakPlan(
                "missing-obligation-map",
                "obligation.coverage",
                lambda text: text.replace("covered_by: SC-1, CH-1, T-1", "covered_by: SC-1"),
            ),
        ),
    ),
    QualityCase(
        id="issue-handoff-protected-behavior",
        request=_sealed_handoff(
            "issue",
            '<!-- issue-handoff-metadata -->\n```json\n{"status":"plan-ready"}\n```\n'
            "## Outcome and Scope\n"
            "Return empty string for absent names.\n"
            "## Constraints and Protected Behavior\n"
            "Protect current strip behavior for present names.\n"
            "## Risks and Open Questions\n"
            "Incidental prose must not be used as an obligation anchor.\n",
        ),
        obligations=_manifest(
            obligation="fix absent names while protecting strip behavior",
            anchor="Protect current strip behavior",
            path="src/names.py",
            claim="root cause is absent-value handling before strip",
            protected="present names remain stripped exactly as today",
            verification=["fails before the fix", "passes after the fix"],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Fix absent names with protected strip behavior",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Protect current strip behavior",
            obligation="fix absent names while protecting strip behavior",
            source="issue",
            change="return empty string for absent values before stripping present names",
            fact_claim="root cause is absent-value handling before strip",
            sc_unchanged="present names remain stripped exactly as today",
            verification_then="the case fails before the fix and passes after the fix with protected strip behavior",
        ),
        weak=(
            WeakPlan(
                "lost-protected-behavior",
                "record.invalid",
                lambda text: text.replace(
                    "unchanged: present names remain stripped exactly as today",
                    "unchanged: TBD",
                ),
            ),
            WeakPlan(
                "incidental-anchor",
                "obligation.anchor",
                lambda text: text.replace(
                    "Protect current strip behavior",
                    "Incidental prose must not be used",
                ),
            ),
        ),
    ),
    QualityCase(
        id="multi-finding-audit-selection",
        request=_sealed_handoff(
            "audit",
            "# Audit\n## Issue FND-2\nNormalize absent values safely.\n## Issue FND-9\nUnrelated finding.\n",
        ),
        obligations=_manifest(
            obligation="remediate selected finding FND-2 absent-value normalization",
            anchor="Normalize absent values safely",
            path="src/names.py",
            claim="root cause is absent-value handling in normalize_name",
            protected="present names remain stripped",
            verification=["fails before the fix", "passes after the fix"],
        ),
        build_repo=_names_base,
        golden=_base_plan(
            title="Remediate selected audit finding",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Normalize absent values safely",
            obligation="remediate selected finding FND-2 absent-value normalization",
            source="audit",
            change="return empty string for absent values before stripping present names",
            fact_claim="root cause is absent-value handling in normalize_name",
            sc_unchanged="present names remain stripped",
            verification_then="the case fails before the fix and passes after the fix and absent values normalize safely",
        ),
        weak=(
            WeakPlan(
                "wrong-finding-anchor",
                "obligation.anchor",
                lambda text: text.replace("Normalize absent values safely", "Unrelated finding"),
            ),
            WeakPlan(
                "missing-fail-before",
                "verification.regression",
                lambda text: text.replace("fails before the fix and passes after the fix", "passes after the fix"),
            ),
        ),
        handoff_item="FND-2",
    ),
)
