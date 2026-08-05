from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
RUNTIME_SPEC = importlib.util.spec_from_file_location("plan_change_v7_runtime", SCRIPTS / "plan_runtime.py")
if RUNTIME_SPEC is None or RUNTIME_SPEC.loader is None:
    raise RuntimeError("cannot load plan-change v7 runtime")
RUNTIME = importlib.util.module_from_spec(RUNTIME_SPEC)
sys.modules[RUNTIME_SPEC.name] = RUNTIME
RUNTIME_SPEC.loader.exec_module(RUNTIME)

DEFAULT_REQUEST = "Fix absent names so normalize_name returns an empty string for absent values.\n"


def make_repo(root: Path, *, git: bool = False) -> Path:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "__init__.py").write_text("# package: names\n", encoding="utf-8")
    (root / "src" / "names.py").write_text(
        "def normalize_name(value: str | None) -> str:\n"
        "    return '' if value is None else value.strip()\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_names.py").write_text(
        "from src.names import normalize_name\n\n"
        "def test_none():\n"
        "    assert normalize_name(None) == ''\n",
        encoding="utf-8",
    )
    if git:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    return root


def tiny_plan(*, fact_kind: str = "source", metadata: str | None = None, request_anchor: str = "Fix absent names") -> str:
    metadata = metadata or '{"intent":"bug-fix","tier":"tiny","risk_domains":[]}'
    extra = ""
    if fact_kind == "function-signature":
        extra = " | parameters: value | returns: str | async: false"
    return f"""# Fix absent-name normalization

<!-- plan-contract: 7 -->
<!-- plan-metadata: {metadata} -->

## Obligations
RQ-1: source: request | anchor: {request_anchor} | obligation: absent input names must normalize to an empty string | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an absent input name | when: normalize_name handles the value | then: it returns an empty string | unchanged: non-null names remain stripped

## Evidence
F-1: kind: {fact_kind} | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns absent-name normalization{extra}

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: return the empty string for absent values before stripping present names | depends_on: none | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present input cases | when: the targeted names tests execute | then: the case fails before the fix and passes after the fix with absent input empty and present input stripped | command: python -m pytest tests/test_names.py -q
"""


def high_risk_plan() -> str:
    return """# Harden tenant name authorization

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"high-risk","risk_domains":["security"]} -->

## Obligations
RQ-1: source: request | anchor: unauthorized tenant | obligation: deny unauthorized tenant names before normalization | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an unauthorized tenant name request | when: normalization is invoked | then: the request is denied before normalization | unchanged: authorized names remain normalized

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalization currently owns the input boundary

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: enforce tenant authorization before normalizing any supplied name value | depends_on: none | locality: shared | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: changed | path: tests/test_names.py | owner: CH-1 | reason: F-1 authorization denial must be covered by caller tests

## Boundaries and Risks
B-1: class: tenant authorization | evidence: F-1 | flow: request principal -> authorization decision -> name normalization
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: unauthorized tenant names could cross the trust boundary

## Verification
T-1: covers: SC-1, CH-1 | given: authorized and unauthorized tenant principals | when: targeted authorization tests execute | then: the case fails before the fix and passes after the fix with unauthorized input denied | command: python -m pytest tests/test_names.py -q
"""


def new_file_plan() -> str:
    return """# Add a names facade

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: names facade | obligation: add a facade that delegates normalization without breaking direct imports | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: a caller importing the names facade | when: it normalizes a value | then: the package delegates to normalize_name | unchanged: direct imports remain valid

## Evidence
F-1: kind: directory-ownership | path: src/__init__.py | lines: 1-1 | anchor: package | claim: the src package owns new facade modules | directory: src

## Implementation
CH-1: path: src/names_facade.py | anchor: src package facade owner | status: new | owner: F-1 | change: add a facade that delegates name normalization to the existing package implementation | depends_on: none | locality: shared | reversibility: reversible

## Propagation
P-1: surface: consumer | disposition: changed | path: src/names_facade.py | owner: CH-1 | reason: F-1 new facade path is the planned consumer surface

## Verification
T-1: covers: SC-1, CH-1 | given: direct and facade imports | when: targeted facade tests execute | then: both imports produce identical normalized values | command: python -m pytest tests/test_names.py -q
"""


def generated_file_plan() -> str:
    return """# Generate the names adapter

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: generated name adapters | obligation: generate the declared adapter module from the owned generator | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: generated name adapters | when: the generator executes | then: it writes the declared adapter module | unchanged: handwritten normalization remains authoritative

## Evidence
F-1: kind: generated-from | path: tools/gen_names.py | lines: 1-2 | anchor: generated_names | claim: the generator owns the declared output | generator: tools/gen_names.py | output: src/generated_names.py

## Implementation
CH-1: path: src/generated_names.py | anchor: generated names output | status: new | owner: F-1 | change: generate an adapter that delegates to the handwritten name normalizer | depends_on: none | locality: local | reversibility: reversible

## Propagation
P-1: surface: generated | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: F-1 bounded sweep found no additional callers beyond the generator output

## Verification
T-1: covers: SC-1, CH-1 | given: a clean generated output | when: the generator and targeted tests execute | then: regeneration is stable and delegation passes | command: python tools/gen_names.py && python -m pytest tests/test_names.py -q
"""


def migration_plan() -> str:
    return """# Migrate normalized names to the durable schema

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"migration","tier":"high-risk","risk_domains":["migration","durable-state"]} -->

## Obligations
RQ-1: source: request | anchor: durable schema | obligation: migrate stored names through an idempotent normalization path | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: stored names from the prior schema | when: the migration runs | then: every value is normalized once | unchanged: already-normalized names remain stable

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name defines the durable value transformation

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: expose an idempotent transformation for the durable-state migration | depends_on: none | locality: shared | reversibility: reversible

## Propagation
P-1: surface: schema | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1 durable transformation owns the migration surface

## Boundaries and Risks
B-1: class: durable schema boundary | evidence: F-1 | flow: stored legacy value -> idempotent normalization -> migrated value
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: interrupted migration could leave mixed durable representations

## Verification
T-1: covers: SC-1, CH-1 | given: legacy, migrated, and interrupted-state fixtures | when: migration verification executes twice | then: all values converge without a second mutation | command: python -m pytest tests/test_names.py -q

## Rollout and Rollback
Deploy in bounded batches with checkpoint counts; stop on divergence and restore the last durable snapshot before retrying.
"""
