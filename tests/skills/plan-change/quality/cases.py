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
    _write_file(root, "src/__init__.py", "from src.names import normalize_name\n\n__all__ = ['normalize_name']\n")
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


def _branching_repo(root: Path) -> None:
    _names_base(root)
    _write_file(root, "src/left.py", "LEFT = 1\n")
    _write_file(root, "src/right.py", "RIGHT = 1\n")
    _write_file(root, "src/merge.py", "MERGE = LEFT + RIGHT if False else 0\n")


def _multi_owner_repo(root: Path) -> None:
    _names_base(root)
    _write_file(
        root,
        "src/gateway.py",
        "from src.names import normalize_name\n\ndef gateway(value):\n    return normalize_name(value)\n",
    )
    _write_file(
        root,
        "src/__init__.py",
        "from src.names import normalize_name\nfrom src.gateway import gateway\n\n__all__ = ['normalize_name', 'gateway']\n",
    )


def _config_repo(root: Path) -> None:
    _names_base(root)
    _write_file(root, "config/settings.toml", "retry_limit = 3\n")


def _generated_repo(root: Path) -> None:
    _names_base(root)
    _write_file(
        root,
        "tools/gen_model.py",
        "OUTPUT = 'src/generated_model.py'\n\ndef generate():\n    Path = __import__('pathlib').Path\n    Path(OUTPUT).write_text('VALUE = 1\\n')\n",
    )


def _migration_repo(root: Path) -> None:
    _names_base(root)
    _write_file(root, "src/schema.py", "SCHEMA = {'name': 'string'}\n")
    _write_file(root, "src/old_reader.py", "def read_old(event):\n    return event['name']\n")
    _write_file(root, "src/new_writer.py", "def write_new(name):\n    return {'name': name}\n")


def _concurrency_repo(root: Path) -> None:
    _names_base(root)
    _write_file(
        root,
        "src/retry_state.py",
        "STATE = {'value': None}\n\ndef apply(value):\n    STATE['value'] = value\n    return STATE['value']\n",
    )


def _external_repo(root: Path) -> None:
    _names_base(root)
    _write_file(
        root,
        "src/external_client.py",
        "def sync_name(name):\n    return {'ack': 'maybe', 'token': None}\n",
    )


def _optimization_repo(root: Path) -> None:
    _names_base(root)
    _write_file(root, "bench/measure_normalize.py", "def p95(samples):\n    return sorted(samples)[int(0.95 * len(samples))]\n")


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
    owner_path: str | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "O1",
            "obligation": obligation,
            "anchor": anchor,
            "planned_paths": [{"path": path}],
            "owner_evidence": [
                {
                    "path": owner_path
                    or (path if path.endswith((".py", ".toml", ".json")) else "src/names.py"),
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
            propagation=[
                {"disposition": "changed", "path": "src/caller.py", "owner": "CH-1"},
                {"disposition": "changed", "path": "src/__init__.py", "owner": "CH-1"},
            ],
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
P-2: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-1 | reason: F-1 package re-export must keep normalize_name public
""",
        ),
        weak=(
            WeakPlan(
                "missing-caller-propagation",
                "propagation_surfaces",
                lambda text: text.replace(
                    "P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 caller imports the shared normalize seam\n",
                    "",
                ),
            ),
            WeakPlan(
                "missing-reexport-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "P-2: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-1 | reason: F-1 package re-export must keep normalize_name public\n",
                    "",
                ).replace(
                    "P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 caller imports the shared normalize seam\n",
                    "P-1: surface: caller | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 restates the owner path only\n",
                ),
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
            propagation=[{"disposition": "changed", "path": "src/names.py", "owner": "CH-1"}],
        ),
        build_repo=_config_repo,
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
P-1: surface: caller | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 name sync consumers read the updated retry_limit
""",
        ),
        weak=(
            WeakPlan("missing-config-evidence", "record.invalid", lambda text: text.replace("kind: config-key", "kind: source")),
            WeakPlan(
                "missing-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: caller | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 name sync consumers read the updated retry_limit\n",
                    "\n",
                ),
            ),
            WeakPlan(
                "owner-path-only",
                "propagation.required",
                lambda text: text.replace(
                    "disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 name sync consumers read the updated retry_limit",
                    "disposition: changed | path: config/settings.toml | owner: CH-1 | reason: F-1 restates the owning config path",
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
            owner_path="tools/gen_model.py",
            propagation=[
                {
                    "disposition": "out-of-scope",
                    "path": "src/names.py",
                    "owner": "CH-1",
                }
            ],
        ),
        build_repo=_generated_repo,
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
        obligations=[
            {
                "id": "O1",
                "obligation": "migrate public name schema with compatibility",
                "anchor": "Migrate public name schema",
                "planned_paths": [
                    {"path": "src/old_reader.py"},
                    {"path": "src/new_writer.py"},
                    {"path": "src/schema.py"},
                ],
                "owner_evidence": [
                    {"path": "src/schema.py", "claim": "SCHEMA owns the public contract shape"},
                    {"path": "src/old_reader.py", "claim": "old_reader accepts compatibility shape"},
                    {"path": "src/new_writer.py", "claim": "new_writer emits the migrated shape"},
                ],
                "dependencies": [
                    {"ch": "CH-1", "depends_on": []},
                    {"ch": "CH-2", "depends_on": ["CH-1"]},
                    {"ch": "CH-3", "depends_on": ["CH-2"]},
                ],
                "propagation": [
                    {"disposition": "changed", "path": "src/old_reader.py", "owner": "CH-1"},
                    {"disposition": "changed", "path": "src/new_writer.py", "owner": "CH-2"},
                    {"disposition": "changed", "path": "src/schema.py", "owner": "CH-3"},
                ],
                "protected_behavior": [{"text": "old readers keep working through the window"}],
                "risk_rollout": [
                    {"risk": "mixed-version readers could reject the new field", "rollout": "compatibility window"},
                ],
                "verification": [{"must_include": ["compatibility checks pass"]}],
            }
        ],
        build_repo=_migration_repo,
        golden="""# Migrate public name schema

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"migration","tier":"high-risk","risk_domains":["public-contract","migration"]} -->

## Obligations
RQ-1: source: request | anchor: Migrate public name schema | obligation: migrate public name schema with compatibility | covered_by: SC-1, CH-1, CH-2, CH-3, T-1

## Outcome
SC-1: given: mixed-version schema traffic | when: migration runs | then: readers and writers converge on the new shape | unchanged: old readers keep working through the window

## Evidence
F-1: kind: source | path: src/schema.py | lines: 1-1 | anchor: SCHEMA | claim: SCHEMA owns the public contract shape
F-2: kind: source | path: src/old_reader.py | lines: 1-2 | anchor: read_old | claim: old_reader accepts compatibility shape
F-3: kind: source | path: src/new_writer.py | lines: 1-2 | anchor: write_new | claim: new_writer emits the migrated shape

## Implementation
CH-1: path: src/old_reader.py | anchor: read_old | status: existing | evidence: F-2 | change: accept both old and new schema shapes during the compatibility window | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/new_writer.py | anchor: write_new | status: existing | evidence: F-3 | change: emit the new schema shape after readers accept it | depends_on: CH-1 | locality: shared | reversibility: reversible
CH-3: path: src/schema.py | anchor: SCHEMA | status: existing | evidence: F-1 | change: remove the compatibility field after writers and readers converge | depends_on: CH-2 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: changed | path: src/old_reader.py | owner: CH-1 | reason: F-2 readers must accept mixed shapes first
P-2: surface: caller | disposition: changed | path: src/new_writer.py | owner: CH-2 | reason: F-3 writers emit only after readers accept
P-3: surface: contract | disposition: changed | path: src/schema.py | owner: CH-3 | reason: F-1 schema cleanup follows writer convergence
P-4: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-1 | reason: F-2 compatibility checks cover reader acceptance
P-5: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-2 | reason: F-3 writer emission is covered by compatibility checks
P-6: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-3 | reason: F-1 schema cleanup is covered by compatibility checks

## Boundaries and Risks
B-1: class: public schema boundary | evidence: F-1 | flow: old schema readers -> compatibility window -> new schema writers
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: mixed-version readers could reject the new field

## Verification
T-1: covers: SC-1, CH-1, CH-2, CH-3 | given: mixed reader and writer fixtures | when: migration verification executes | then: compatibility checks pass | command: python -m pytest tests/test_names.py -q

## Rollout and Rollback
Deploy schema writers after readers in one compatibility window. If validation divergence appears, roll back writers and restore the previous schema snapshot.
""",
        weak=(
            WeakPlan("missing-rollout", "section.order", lambda text: text.split("\n## Rollout and Rollback", 1)[0] + "\n"),
            WeakPlan(
                "wrong-dependency",
                "dependency.missing",
                lambda text: text.replace("depends_on: CH-1 | locality: shared | reversibility: reversible\nCH-3:", "depends_on: CH-9 | locality: shared | reversibility: reversible\nCH-3:"),
            ),
            WeakPlan(
                "missing-reader-change",
                "dependency.missing",
                lambda text: text.replace("CH-1: path: src/old_reader.py | anchor: read_old | status: existing | evidence: F-2 | change: accept both old and new schema shapes during the compatibility window | depends_on: none | locality: shared | reversibility: reversible\n", ""),
            ),
            WeakPlan(
                "rollout-without-recovery",
                "rollout.invalid",
                lambda text: text.replace(
                    "Deploy schema writers after readers in one compatibility window. If validation divergence appears, roll back writers and restore the previous schema snapshot.",
                    "Deploy schema writers after readers in one compatibility window.",
                ),
            ),
        ),
    ),
    QualityCase(
        id="concurrency-idempotency",
        request="Make retry state idempotent under concurrent retries.\n",
        obligations=_manifest(
            obligation="idempotent retry state under concurrent retries",
            anchor="idempotent under concurrent retries",
            path="src/retry_state.py",
            claim="retry_state owns concurrent retry mutation",
            protected="stripped values stay stable under retry",
            verification=["fails before the fix", "passes after the fix", "idempotent"],
            propagation=[{"disposition": "unchanged", "path": "src/caller.py", "owner": "CH-1"}],
            risk_rollout=[{"risk": "overlapping retries could mutate a value twice"}],
        ),
        build_repo=_concurrency_repo,
        golden=_base_plan(
            title="Make retry state idempotent",
            metadata='{"intent":"bug-fix","tier":"high-risk","risk_domains":["concurrency"]}',
            request_anchor="idempotent under concurrent retries",
            obligation="idempotent retry state under concurrent retries",
            change="make apply idempotent so concurrent retries return the same stored value without double mutation",
            path="src/retry_state.py",
            anchor="apply",
            fact_path="src/retry_state.py",
            fact_lines="1-5",
            fact_claim="retry_state owns concurrent retry mutation",
            locality="shared",
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
            WeakPlan(
                "wrong-owner",
                "owner_root_cause_evidence",
                lambda text: text.replace(
                    "claim: retry_state owns concurrent retry mutation",
                    "claim: normalize_name owns concurrent retry mutation",
                ),
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
            propagation=[{"disposition": "changed", "path": "src/caller.py", "owner": "CH-1"}],
            risk_rollout=[
                {"risk": "ambiguous acknowledgements could double-apply sync", "rollout": "canary"},
            ],
        ),
        build_repo=_external_repo,
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
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 callers must tolerate retryable ambiguous acknowledgements

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
                    "disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 callers must tolerate retryable ambiguous acknowledgements",
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
            "- Constraint: preserve present-name strip contract\n"
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
        golden="""# Implement selected name gateway

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: design | category: decision | anchor: NameGateway.normalize owns absent-name handling | obligation: implement selected NameGateway.normalize boundary | covered_by: SC-1, CH-1, T-1
RQ-2: source: design | category: constraint | anchor: preserve present-name strip contract | obligation: preserve the strip contract while introducing the boundary | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an observable setup | when: the planned action runs | then: the observable result occurs | unchanged: strip behavior remains

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name is the chosen boundary owner

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: introduce the selected NameGateway.normalize boundary while preserving current strip behavior | depends_on: none | locality: shared | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1 callers must adopt the selected boundary

## Verification
T-1: covers: SC-1, CH-1 | given: targeted cases | when: tests execute | then: selected boundary holds | command: python -m pytest tests/test_names.py -q
""",
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
            WeakPlan(
                "missing-constraint-category",
                "obligation.coverage",
                lambda text: text.replace(
                    "RQ-2: source: design | category: constraint | anchor: preserve present-name strip contract | obligation: preserve the strip contract while introducing the boundary | covered_by: SC-1, CH-1, T-1\n",
                    "",
                ),
            ),
        ),
    ),
    QualityCase(
        id="optimization-handoff-inheritance",
        request=_sealed_handoff(
            "optimization",
            "- Selected candidate: C-1\n"
            "- H-1: next: plan-ready | candidate: C-1 | measure: p95 latency | workflow: normalize_name hot path\n"
            "- C-1: cache normalize_name for repeated inputs\n"
            "- C-9: rejected speculative rewrite\n",
        ),
        obligations=[
            {
                "id": "O1",
                "obligation": "cache normalize_name for the selected workflow measure",
                "anchor": "cache normalize_name for repeated inputs",
                "planned_paths": [{"path": "src/names.py"}],
                "owner_evidence": [{"path": "src/names.py", "claim": "normalize_name owns the measured hot path"}],
                "dependencies": [{"ch": "CH-1", "depends_on": []}],
                "propagation": [{"disposition": "out-of-scope", "path": "src/caller.py", "owner": "CH-1"}],
                "protected_behavior": [{"text": "empty-string behavior remains"}],
                "risk_rollout": [],
                "verification": [
                    {
                        "must_include": ["p95 measure improves", "baseline", "threshold"],
                        "must_command": ["bench/measure_normalize.py"],
                    }
                ],
            }
        ],
        build_repo=_optimization_repo,
        golden="""# Cache normalize_name path

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: optimization | category: candidate | anchor: cache normalize_name for repeated inputs | obligation: cache normalize_name for the selected workflow measure | covered_by: SC-1, CH-1, T-1
RQ-2: source: optimization | category: workflow | anchor: normalize_name hot path | obligation: target the normalize_name hot path workflow | covered_by: SC-1, CH-1, T-1
RQ-3: source: optimization | category: measure | anchor: p95 latency | obligation: improve the p95 latency measure against baseline | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an observable setup | when: the planned action runs | then: the observable result occurs | unchanged: empty-string behavior remains

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns the measured hot path

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: cache normalize_name results for repeated identical inputs while preserving empty-string behavior | depends_on: none | locality: local | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: out-of-scope | path: src/caller.py | owner: CH-1 | reason: F-1 bounded sweep found no extra measure owners beyond the hot path

## Verification
T-1: covers: SC-1, CH-1 | given: repeated normalize inputs with recorded baseline | when: the measure harness executes | then: p95 measure improves above the recorded baseline threshold | command: python bench/measure_normalize.py
""",
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
                "unit-test-only-verification",
                "verification_coverage",
                lambda text: text.replace(
                    "command: python bench/measure_normalize.py",
                    "command: python -m pytest tests/test_names.py -q",
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
            "Constraint: keep the public normalize_name signature stable.\n"
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
        golden="""# Fix absent names with protected strip behavior

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Obligations
RQ-1: source: issue | category: outcome | anchor: Return empty string for absent names | obligation: return empty string for absent names | covered_by: SC-1, CH-1, T-1
RQ-2: source: issue | category: protected-behavior | anchor: Protect current strip behavior | obligation: fix absent names while protecting strip behavior | covered_by: SC-1, CH-1, T-1
RQ-3: source: issue | category: constraint | anchor: keep the public normalize_name signature stable | obligation: keep the public normalize_name signature stable | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an observable setup | when: the planned action runs | then: the observable result occurs | unchanged: present names remain stripped exactly as today

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: root cause is absent-value handling before strip

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: return empty string for absent values before stripping present names | depends_on: none | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: targeted cases | when: tests execute | then: the case fails before the fix and passes after the fix with protected strip behavior | command: python -m pytest tests/test_names.py -q
""",
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
    QualityCase(
        id="branching-deps-incomplete",
        request="Add branching left and right owners before merge.\n",
        obligations=[
            {
                "id": "O1",
                "obligation": "add branching left and right owners before merge",
                "anchor": "branching left and right",
                "planned_paths": [
                    {"path": "src/names.py"},
                    {"path": "src/left.py"},
                    {"path": "src/right.py"},
                    {"path": "src/merge.py"},
                ],
                "owner_evidence": [
                    {"path": "src/names.py", "claim": "normalize_name owns the root seam"},
                    {"path": "src/left.py", "claim": "left branch owns LEFT"},
                    {"path": "src/right.py", "claim": "right branch owns RIGHT"},
                    {"path": "src/merge.py", "claim": "merge consumes both branches"},
                ],
                "dependencies": [
                    {"ch": "CH-1", "depends_on": []},
                    {"ch": "CH-2", "depends_on": ["CH-1"]},
                    {"ch": "CH-3", "depends_on": ["CH-1"]},
                    {"ch": "CH-4", "depends_on": ["CH-2", "CH-3"]},
                ],
                "propagation": [
                    {"disposition": "changed", "path": "src/left.py", "owner": "CH-1"},
                    {"disposition": "changed", "path": "src/right.py", "owner": "CH-1"},
                    {"disposition": "changed", "path": "src/merge.py", "owner": "CH-2"},
                ],
                "protected_behavior": [{"text": "unrelated callers remain untouched"}],
                "risk_rollout": [],
                "verification": [{"must_include": ["both branches and merge resolve"]}],
            }
        ],
        build_repo=_branching_repo,
        golden="""# Add branching owners before merge

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: branching left and right | obligation: add branching left and right owners before merge | covered_by: SC-1, CH-1, CH-2, CH-3, CH-4, T-1

## Outcome
SC-1: given: left and right branch modules | when: merge imports resolve | then: both branches and merge resolve | unchanged: unrelated callers remain untouched

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns the root seam
F-2: kind: source | path: src/left.py | lines: 1-1 | anchor: LEFT | claim: left branch owns LEFT
F-3: kind: source | path: src/right.py | lines: 1-1 | anchor: RIGHT | claim: right branch owns RIGHT
F-4: kind: source | path: src/merge.py | lines: 1-1 | anchor: MERGE | claim: merge consumes both branches

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: keep normalize_name as the shared root seam for branching work | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/left.py | anchor: LEFT | status: existing | evidence: F-2 | change: expose the left branch constant for merge | depends_on: CH-1 | locality: shared | reversibility: reversible
CH-3: path: src/right.py | anchor: RIGHT | status: existing | evidence: F-3 | change: expose the right branch constant for merge | depends_on: CH-1 | locality: shared | reversibility: reversible
CH-4: path: src/merge.py | anchor: MERGE | status: existing | evidence: F-4 | change: combine left and right branch constants after both land | depends_on: CH-2, CH-3 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: consumer | disposition: changed | path: src/left.py | owner: CH-1 | reason: F-2 left branch is a distinct owned surface from the root seam
P-2: surface: consumer | disposition: changed | path: src/right.py | owner: CH-1 | reason: F-3 right branch is a distinct owned surface from the root seam
P-3: surface: consumer | disposition: changed | path: src/merge.py | owner: CH-2 | reason: F-4 merge consumes the left branch after it exists
P-4: surface: consumer | disposition: changed | path: src/merge.py | owner: CH-3 | reason: F-4 merge consumes the right branch after it exists
P-5: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-4 | reason: F-4 merge verification covers both branches

## Verification
T-1: covers: SC-1, CH-1, CH-2, CH-3, CH-4 | given: left right and merge modules | when: imports execute | then: both branches and merge resolve | command: python -m pytest tests/test_names.py -q
""",
        weak=(
            WeakPlan(
                "missing-right-branch",
                "planned_paths",
                lambda text: text.replace(
                    "CH-3: path: src/right.py | anchor: RIGHT | status: existing | evidence: F-3 | change: expose the right branch constant for merge | depends_on: CH-1 | locality: shared | reversibility: reversible\n",
                    "",
                )
                .replace(", CH-3", "")
                .replace("CH-2, CH-3", "CH-2")
                .replace(
                    "P-4: surface: consumer | disposition: changed | path: src/merge.py | owner: CH-3 | reason: F-4 merge consumes the right branch after it exists\n",
                    "",
                )
                .replace(
                    "P-2: surface: consumer | disposition: changed | path: src/right.py | owner: CH-1 | reason: F-3 right branch is a distinct owned surface from the root seam\n",
                    "",
                ),
            ),
            WeakPlan(
                "wrong-merge-dependency",
                "dependency_ordering",
                lambda text: text.replace(
                    "depends_on: CH-2, CH-3 | locality: shared | reversibility: reversible",
                    "depends_on: CH-1 | locality: shared | reversibility: reversible",
                ),
            ),
        ),
    ),
    QualityCase(
        id="multi-owner-shared-surface",
        request="Own normalize_name and gateway with shared re-export.\n",
        obligations=[
            {
                "id": "O1",
                "obligation": "own normalize_name and gateway with shared re-export",
                "anchor": "normalize_name and gateway",
                "planned_paths": [
                    {"path": "src/names.py"},
                    {"path": "src/gateway.py"},
                    {"path": "src/__init__.py"},
                ],
                "owner_evidence": [
                    {"path": "src/names.py", "claim": "normalize_name owns strip behavior"},
                    {"path": "src/gateway.py", "claim": "gateway owns the facade entry"},
                ],
                "dependencies": [
                    {"ch": "CH-1", "depends_on": []},
                    {"ch": "CH-2", "depends_on": ["CH-1"]},
                    {"ch": "CH-3", "depends_on": ["CH-1", "CH-2"]},
                ],
                "propagation": [
                    {"disposition": "changed", "path": "src/__init__.py", "owner": "CH-1"},
                    {"disposition": "changed", "path": "src/__init__.py", "owner": "CH-2"},
                ],
                "protected_behavior": [{"text": "strip behavior remains identical"}],
                "risk_rollout": [],
                "verification": [{"must_include": ["gateway and re-export tests pass"]}],
            }
        ],
        build_repo=_multi_owner_repo,
        golden="""# Own normalize_name and gateway re-export

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: normalize_name and gateway | obligation: own normalize_name and gateway with shared re-export | covered_by: SC-1, CH-1, CH-2, CH-3, T-1

## Outcome
SC-1: given: gateway and package imports | when: callers import public names | then: gateway and re-export tests pass | unchanged: strip behavior remains identical

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns strip behavior
F-2: kind: source | path: src/gateway.py | lines: 1-4 | anchor: gateway | claim: gateway owns the facade entry
F-3: kind: source | path: src/__init__.py | lines: 1-4 | anchor: __all__ | claim: package re-export publishes both owners

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: keep normalize_name as the strip owner for the shared package | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/gateway.py | anchor: gateway | status: existing | evidence: F-2 | change: keep gateway as the facade owner over normalize_name | depends_on: CH-1 | locality: shared | reversibility: reversible
CH-3: path: src/__init__.py | anchor: __all__ | status: existing | evidence: F-3 | change: re-export normalize_name and gateway together | depends_on: CH-1, CH-2 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-1 | reason: F-3 package re-export must publish normalize_name
P-2: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-2 | reason: F-3 package re-export must publish gateway
P-3: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-3 | reason: F-3 re-export coverage stays in package tests

## Verification
T-1: covers: SC-1, CH-1, CH-2, CH-3 | given: gateway and package imports | when: tests execute | then: gateway and re-export tests pass | command: python -m pytest tests/test_names.py -q
""",
        weak=(
            WeakPlan(
                "owner-path-only-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "P-1: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-1 | reason: F-3 package re-export must publish normalize_name\n"
                    "P-2: surface: consumer | disposition: changed | path: src/__init__.py | owner: CH-2 | reason: F-3 package re-export must publish gateway\n",
                    "P-1: surface: consumer | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 same-path only declaration\n"
                    "P-2: surface: consumer | disposition: changed | path: src/gateway.py | owner: CH-2 | reason: F-2 same-path only declaration\n",
                ),
            ),
            WeakPlan(
                "missing-reexport-change",
                "planned_paths",
                lambda text: text.replace(
                    "CH-3: path: src/__init__.py | anchor: __all__ | status: existing | evidence: F-3 | change: re-export normalize_name and gateway together | depends_on: CH-1, CH-2 | locality: shared | reversibility: reversible\n",
                    "",
                ).replace(", CH-3", "").replace("CH-1, CH-2, CH-3", "CH-1, CH-2"),
            ),
        ),
    ),
    QualityCase(
        id="generic-structured-request-gaps",
        request=(
            "Normalize names with full coverage.\n\n"
            "## Requirements\n"
            "- Fix absent names\n"
            "- Update affected consumers\n\n"
            "## Constraints\n"
            "Must reject non-string inputs.\n"
            "Do not weaken caller contracts.\n"
            "Preserve present-name strip behavior.\n"
        ),
        obligations=[
            {
                "id": "O1",
                "obligation": "absent input names must normalize to an empty string",
                "anchor": "Fix absent names",
                "planned_paths": [{"path": "src/names.py"}, {"path": "src/caller.py"}],
                "owner_evidence": [
                    {"path": "src/names.py", "claim": "normalize_name owns absent-value handling"},
                ],
                "dependencies": [
                    {"ch": "CH-1", "depends_on": []},
                    {"ch": "CH-2", "depends_on": ["CH-1"]},
                ],
                "propagation": [
                    {"disposition": "changed", "path": "src/caller.py", "owner": "CH-1"},
                ],
                "protected_behavior": [{"text": "present-name strip behavior"}],
                "risk_rollout": [],
                "verification": [{"must_include": ["fails before the fix", "passes after the fix"]}],
            }
        ],
        build_repo=_names_base,
        golden="""# Normalize names with structured request coverage

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: Fix absent names | obligation: absent input names must normalize to an empty string | covered_by: SC-1, CH-1, CH-2, T-1
RQ-2: source: request | anchor: Update affected consumers | obligation: update callers that consume normalize_name | covered_by: SC-1, CH-2, T-1
RQ-3: source: request | anchor: Must reject non-string inputs | obligation: reject non-string inputs explicitly | covered_by: SC-1, CH-1, T-1
RQ-4: source: request | anchor: Do not weaken caller contracts | obligation: keep caller contracts intact | covered_by: SC-1, CH-2, T-1
RQ-5: source: request | anchor: Preserve present-name strip behavior | obligation: preserve present-name strip behavior | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: absent and present names | when: normalize_name runs | then: absent values are empty and callers stay valid | unchanged: present-name strip behavior

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns absent-value handling
F-2: kind: source | path: src/caller.py | lines: 1-4 | anchor: run | claim: caller consumes normalize_name

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: return empty for absent values and reject non-string inputs before stripping | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/caller.py | anchor: run | status: existing | evidence: F-2 | change: keep caller contracts while adopting empty absent-name results | depends_on: CH-1 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-2 callers must adopt empty absent-name results
P-2: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-2 | reason: F-2 caller contracts stay covered by tests

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: absent present and non-string inputs | when: targeted tests execute | then: the case fails before the fix and passes after the fix | command: python -m pytest tests/test_names.py -q
""",
        weak=(
            WeakPlan(
                "omitted-second-bullet",
                "obligation.coverage",
                lambda text: text.replace(
                    "RQ-2: source: request | anchor: Update affected consumers | obligation: update callers that consume normalize_name | covered_by: SC-1, CH-2, T-1\n",
                    "",
                ),
            ),
            WeakPlan(
                "omitted-negative-constraint",
                "obligation.coverage",
                lambda text: text.replace(
                    "RQ-4: source: request | anchor: Do not weaken caller contracts | obligation: keep caller contracts intact | covered_by: SC-1, CH-2, T-1\n",
                    "",
                ),
            ),
            WeakPlan(
                "omitted-preserve",
                "obligation.coverage",
                lambda text: text.replace(
                    "RQ-5: source: request | anchor: Preserve present-name strip behavior | obligation: preserve present-name strip behavior | covered_by: SC-1, CH-1, T-1\n",
                    "",
                ),
            ),
            WeakPlan(
                "trivial-anchor",
                "obligation.anchor",
                lambda text: text.replace("anchor: Fix absent names", "anchor: fix", 1),
            ),
            WeakPlan(
                "wrong-rq-source",
                "obligation.source",
                lambda text: text.replace(
                    "RQ-1: source: request | anchor: Fix absent names",
                    "RQ-1: source: design | category: decision | anchor: Fix absent names",
                    1,
                ),
            ),
        ),
    ),
)
