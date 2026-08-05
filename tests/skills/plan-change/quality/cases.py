"""Provider-free plan-quality fixture cases for plan-contract v7."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _sealed_handoff(kind: str, body: str) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"<!-- {kind}-handoff: 1; sha256: {digest} -->\n{body}"


def _write_names_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "__init__.py").write_text("# package\n", encoding="utf-8")
    (root / "src" / "names.py").write_text(
        "def normalize_name(value: str | None) -> str:\n"
        "    return '' if value is None else value.strip()\n",
        encoding="utf-8",
    )
    (root / "src" / "caller.py").write_text(
        "from src.names import normalize_name\n\ndef run(value):\n    return normalize_name(value)\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_names.py").write_text(
        "from src.names import normalize_name\n\ndef test_none():\n    assert normalize_name(None) == ''\n",
        encoding="utf-8",
    )


def _write_schema_repo(root: Path) -> None:
    _write_names_repo(root)
    (root / "src" / "schema.py").write_text(
        "SCHEMA = {'name': 'string'}\n",
        encoding="utf-8",
    )
    (root / "config").mkdir()
    (root / "config" / "settings.toml").write_text("retry_limit = 3\n", encoding="utf-8")
    (root / "tools").mkdir()
    (root / "tools" / "gen_model.py").write_text(
        "OUTPUT = 'src/generated_model.py'\n\ndef generate():\n    Path = __import__('pathlib').Path\n    Path(OUTPUT).write_text('VALUE = 1\\n')\n",
        encoding="utf-8",
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
F-1: kind: {fact_kind} | path: {fact_path} | lines: {fact_lines} | anchor: {anchor} | claim: evidence for the planned change{fact_extra}

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


CASES: tuple[QualityCase, ...] = (
    QualityCase(
        id="tiny-local-bug",
        request="Fix absent names for normalize_name.\n",
        obligations=[{"id": "O1", "obligation": "absent input names must normalize to an empty string", "anchor": "Fix absent names"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Fix absent-name normalization",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Fix absent names",
            obligation="absent input names must normalize to an empty string",
            change="return the empty string for absent values before stripping present names",
            verification_then="the regression fails before the fix and passes after absent input is empty",
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
            WeakPlan("missing-verification-cover", "verification.coverage", lambda text: text.replace("covers: SC-1, CH-1", "covers: SC-1")),
        ),
    ),
    QualityCase(
        id="shared-refactor-callers",
        request="Refactor normalize_name and update callers.\n",
        obligations=[{"id": "O1", "obligation": "preserve normalization while updating callers", "anchor": "update callers"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Refactor name normalization callers",
            metadata='{"intent":"refactor","tier":"standard","risk_domains":[]}',
            request_anchor="update callers",
            obligation="preserve normalization while updating callers",
            change="preserve normalize_name behavior while relocating the shared helper used by callers",
            locality="shared",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1
""",
        ),
        weak=(
            WeakPlan("missing-propagation", "propagation.required", lambda text: text.replace("\n## Propagation\nP-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1\n", "\n")),
        ),
    ),
    QualityCase(
        id="feature-defaults-errors",
        request="Add default empty-name handling with clear errors.\n",
        obligations=[{"id": "O1", "obligation": "default empty-name handling with explicit errors", "anchor": "default empty-name"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Add default empty-name handling",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="default empty-name",
            obligation="default empty-name handling with explicit errors",
            change="default absent names to empty string and raise ValueError for non-string inputs before stripping",
            locality="local",
        ),
        weak=(
            WeakPlan("vague-change", "change.specificity", lambda text: text.replace(
                "default absent names to empty string and raise ValueError for non-string inputs before stripping",
                "improve names",
            )),
        ),
    ),
    QualityCase(
        id="config-dependency-change",
        request="Raise retry_limit configuration for name sync.\n",
        obligations=[{"id": "O1", "obligation": "raise retry_limit for name sync", "anchor": "retry_limit"}],
        build_repo=_write_schema_repo,
        golden=_base_plan(
            title="Raise retry limit configuration",
            metadata='{"intent":"operational","tier":"standard","risk_domains":[]}',
            request_anchor="retry_limit",
            obligation="raise retry_limit for name sync",
            change="increase retry_limit from 3 to 5 while preserving existing timeout behavior",
            path="config/settings.toml",
            anchor="retry_limit",
            fact_kind="config-key",
            fact_path="config/settings.toml",
            fact_lines="1-1",
            fact_extra=" | key: retry_limit | value: 3",
            locality="shared",
            mid_sections="""
## Propagation
P-1: surface: config | disposition: changed | path: config/settings.toml | owner: CH-1 | reason: F-1
""",
        ),
        weak=(
            WeakPlan("missing-config-evidence", "fact.structured", lambda text: text.replace("value: 3", "value: 99")),
        ),
    ),
    QualityCase(
        id="generated-output-ownership",
        request="Generate owned model adapter output.\n",
        obligations=[{"id": "O1", "obligation": "generate owned model adapter output", "anchor": "Generate owned model"}],
        build_repo=_write_schema_repo,
        golden=_base_plan(
            title="Generate model adapter",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="Generate owned model",
            obligation="generate owned model adapter output",
            change="generate the declared model adapter module from the owned generator without hand edits",
            path="src/generated_model.py",
            anchor="OUTPUT",
            status="new",
            evidence="owner: F-1",
            fact_kind="generated-from",
            fact_path="tools/gen_model.py",
            fact_lines="1-4",
            fact_extra=" | generator: tools/gen_model.py | output: src/generated_model.py",
            locality="local",
        ),
        weak=(
            WeakPlan("missing-owner", "change.target", lambda text: text.replace(" | owner: F-1", "")),
        ),
    ),
    QualityCase(
        id="public-contract-migration",
        request="Migrate public name schema with compatibility window.\n",
        obligations=[{"id": "O1", "obligation": "migrate public name schema with compatibility", "anchor": "Migrate public name schema"}],
        build_repo=_write_schema_repo,
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
            locality="shared",
            mid_sections="""
## Propagation
P-1: surface: contract | disposition: changed | path: src/schema.py | owner: CH-1 | reason: F-1

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
        ),
    ),
    QualityCase(
        id="concurrency-idempotency",
        request="Make normalize_name idempotent under concurrent retries.\n",
        obligations=[{"id": "O1", "obligation": "idempotent normalization under concurrent retries", "anchor": "idempotent"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Make normalization idempotent",
            metadata='{"intent":"bug-fix","tier":"high-risk","risk_domains":["concurrency"]}',
            request_anchor="idempotent",
            obligation="idempotent normalization under concurrent retries",
            change="make normalize_name idempotent so concurrent retries return the same stripped value without double mutation",
            locality="shared",
            verification_then="the regression fails before the fix and concurrent retries stay idempotent",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: unchanged | path: src/caller.py | owner: CH-1 | reason: F-1

## Boundaries and Risks
B-1: class: concurrent retry boundary | evidence: F-1 | flow: first attempt -> overlapping retry -> reconciled result
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: overlapping retries could mutate a value twice
""",
        ),
        weak=(
            WeakPlan("missing-risk", "record.invalid", lambda text: text.replace("\n## Boundaries and Risks\nB-1: class: concurrent retry boundary | evidence: F-1 | flow: first attempt -> overlapping retry -> reconciled result\nR-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: overlapping retries could mutate a value twice\n", "\n")),
        ),
    ),
    QualityCase(
        id="external-ambiguous-success",
        request="Handle ambiguous external name sync success.\n",
        obligations=[{"id": "O1", "obligation": "handle ambiguous external sync success", "anchor": "ambiguous external"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Handle ambiguous external sync",
            metadata='{"intent":"feature","tier":"high-risk","risk_domains":["external-integration"]}',
            request_anchor="ambiguous external",
            obligation="handle ambiguous external sync success",
            change="treat ambiguous external sync acknowledgements as retryable until an idempotent success token is observed",
            locality="shared",
            mid_sections="""
## Propagation
P-1: surface: deployment | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1

## Boundaries and Risks
B-1: class: external acknowledgement boundary | evidence: F-1 | flow: request sent -> ambiguous ack -> idempotent confirmation
R-1: severity: P0 | owner: CH-1 | tests: T-1 | risk: ambiguous success could duplicate external side effects
""",
            rollout="""
## Rollout and Rollback
Deploy behind a bounded canary. If duplicate side effects appear, disable the sync path and roll forward with compensation retries.
""",
        ),
        weak=(
            WeakPlan("missing-rollout", "section.order", lambda text: text.split("\n## Rollout and Rollback", 1)[0] + "\n"),
        ),
    ),
    QualityCase(
        id="design-handoff-inheritance",
        request=_sealed_handoff("design", "# Design\nSelected boundary: NameGateway.normalize\n"),
        obligations=[{"id": "O1", "obligation": "implement selected NameGateway.normalize boundary", "anchor": "NameGateway.normalize"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Implement selected name gateway",
            metadata='{"intent":"refactor","tier":"standard","risk_domains":[]}',
            request_anchor="NameGateway.normalize",
            obligation="implement selected NameGateway.normalize boundary",
            source="design",
            change="introduce the selected NameGateway.normalize boundary while preserving current strip behavior",
            locality="shared",
            mid_sections="""
## Propagation
P-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1
""",
        ),
        weak=(
            WeakPlan(
                "missing-propagation",
                "propagation.required",
                lambda text: text.replace(
                    "\n## Propagation\nP-1: surface: caller | disposition: changed | path: src/caller.py | owner: CH-1 | reason: F-1\n",
                    "\n",
                ),
            ),
        ),
    ),
    QualityCase(
        id="optimization-handoff-inheritance",
        request=_sealed_handoff(
            "optimization",
            "# Optimization\n- H-1: next: plan-ready | candidate: cache normalize_name | measure: p95 latency\n",
        ),
        obligations=[{"id": "O1", "obligation": "cache normalize_name for the selected workflow measure", "anchor": "cache normalize_name"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Cache normalize_name path",
            metadata='{"intent":"feature","tier":"standard","risk_domains":[]}',
            request_anchor="cache normalize_name",
            obligation="cache normalize_name for the selected workflow measure",
            source="optimization",
            change="cache normalize_name results for repeated identical inputs while preserving empty-string behavior",
            locality="local",
        ),
        weak=(
            WeakPlan("missing-obligation-map", "obligation.coverage", lambda text: text.replace("covered_by: SC-1, CH-1, T-1", "covered_by: SC-1")),
        ),
    ),
    QualityCase(
        id="issue-handoff-protected-behavior",
        request=_sealed_handoff(
            "issue",
            '<!-- issue-handoff-metadata -->\n```json\n{"status":"plan-ready"}\n```\n'
            "# Issue\nProtect current strip behavior while fixing absent names.\n",
        ),
        obligations=[
            {"id": "O1", "obligation": "fix absent names while protecting strip behavior", "anchor": "Protect current strip behavior"},
        ],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Fix absent names with protected strip behavior",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Protect current strip behavior",
            obligation="fix absent names while protecting strip behavior",
            source="issue",
            change="return empty string for absent values before stripping present names",
            sc_unchanged="present names remain stripped exactly as today",
            verification_then="the regression fails before the fix and protected strip behavior remains",
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
        ),
    ),
    QualityCase(
        id="multi-finding-audit-selection",
        request=_sealed_handoff(
            "audit",
            "# Audit\n## Issue FND-2\nNormalize absent values safely.\n## Issue FND-9\nUnrelated finding.\n",
        ),
        obligations=[{"id": "O1", "obligation": "remediate selected finding FND-2 absent-value normalization", "anchor": "Normalize absent values safely"}],
        build_repo=_write_names_repo,
        golden=_base_plan(
            title="Remediate selected audit finding",
            metadata='{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
            request_anchor="Normalize absent values safely",
            obligation="remediate selected finding FND-2 absent-value normalization",
            source="audit",
            change="return empty string for absent values before stripping present names",
            verification_then="the regression fails before the fix and absent values normalize safely",
        ),
        weak=(
            WeakPlan("wrong-finding-anchor", "obligation.anchor", lambda text: text.replace("Normalize absent values safely", "Unrelated finding")),
        ),
        handoff_item="FND-2",
    ),
)
