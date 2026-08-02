#!/usr/bin/env python3
"""Generate the committed synthetic benchmark repositories from fixed domain models."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.generators.realistic_portfolio import generate as generate_realistic_fixture  # noqa: E402
from tools.benchmarks.fixtures import FixtureTree, inspect_fixture_tree  # noqa: E402

REPOS = ROOT / "benchmarks" / "repos"
SCRATCH_ROOT = ROOT / ".scratch" / "benchmarks"

FEATURE_MODEL = {
    "evaluation": ["segment", "constraint", "context", "prerequisite", "variant"],
    "rollouts": ["progressive", "scheduled", "percentage", "emergency", "regional"],
    "persistence": ["flag", "environment", "audit", "revision"],
    "api": ["flag", "environment", "evaluation", "admin"],
    "jobs": ["rollout", "cleanup", "reconciliation"],
}
FEATURE_ROLES = ("model", "repository", "service", "policy")

SUBSCRIPTION_MODEL = {
    "accounts": ["tenant", "member", "organization", "profile", "access", "session", "identity"],
    "catalog": ["plan", "price", "product", "coupon", "tax", "currency", "offer"],
    "billing": ["renewal", "invoice", "payment", "attempt", "refund", "ledger", "gateway", "credit"],
    "entitlements": ["grant", "feature", "quota", "license", "seat", "usage"],
    "notifications": ["renewal", "receipt", "failure", "digest", "webhook", "template", "delivery"],
    "reporting": ["revenue", "churn", "cohort", "invoice", "usage", "export"],
    "platform": ["clock", "idempotency", "outbox", "tracing", "configuration", "health"],
}
SUBSCRIPTION_ROLES = ("model", "repository", "service", "policy", "handler")

FEATURE_CORE = {
    "src/evaluation/segment_matcher.py": '''from __future__ import annotations


def matches_segment(attributes: dict[str, str], required: dict[str, str]) -> bool:
    """Return whether every required attribute is present with the expected value."""
    return all(attributes.get(key) == value for key, value in required.items())
''',
    "src/rollouts/progressive_rollout.py": '''from __future__ import annotations


def rollout_percentage(start: int, increment: int, maximum: int) -> int:
    """Advance one rollout step without exceeding the configured maximum."""
    if increment < 0:
        raise ValueError("increment must be non-negative")
    return min(start + increment, maximum)
''',
    "src/persistence/flag_repository.py": '''from __future__ import annotations


class FlagRepository:
    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}

    def save(self, key: str, enabled: bool) -> None:
        self._flags[key] = enabled

    def get(self, key: str) -> bool | None:
        return self._flags.get(key)
''',
    "src/api/evaluation_routes.py": '''from __future__ import annotations

from src.evaluation.segment_matcher import matches_segment


def evaluate(attributes: dict[str, str], required: dict[str, str]) -> dict[str, bool]:
    return {"matched": matches_segment(attributes, required)}
''',
    "config/evaluator.yaml": "evaluation:\n  cache_ttl_seconds: 30\n  max_prerequisite_depth: 8\n",
    "schemas/flag-event.json": json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["flag_key", "environment", "enabled"],
            "properties": {
                "flag_key": {"type": "string"},
                "environment": {"type": "string"},
                "enabled": {"type": "boolean"},
            },
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
}

SUBSCRIPTION_CORE = {
    "src/billing/renewal_orchestrator.py": '''from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenewalRequest:
    subscription_id: str
    cycle: str
    amount_cents: int


def renewal_key(request: RenewalRequest) -> str:
    """Return the stable identity shared by retries of one billing cycle."""
    return f"{request.subscription_id}:{request.cycle}"


def process_renewal(request: RenewalRequest, seen: set[str]) -> bool:
    key = renewal_key(request)
    if key in seen:
        return False
    seen.add(key)
    return True
''',
    "src/billing/gateway_client.py": '''from __future__ import annotations


class AmbiguousGatewayTimeout(RuntimeError):
    """The provider may have accepted a request before the response timed out."""


def charge(idempotency_key: str, amount_cents: int) -> dict[str, object]:
    if not idempotency_key:
        raise ValueError("idempotency key is required")
    return {"key": idempotency_key, "amount_cents": amount_cents, "accepted": True}
''',
    "src/billing/payment_attempt_repository.py": '''from __future__ import annotations


class PaymentAttemptRepository:
    def __init__(self) -> None:
        self._attempts: set[str] = set()

    def reserve(self, attempt_key: str) -> bool:
        if attempt_key in self._attempts:
            return False
        self._attempts.add(attempt_key)
        return True
''',
    "src/notifications/renewal_notice_job.py": '''from __future__ import annotations


def renewal_notice(subscription_id: str, successful: bool) -> dict[str, str]:
    state = "renewed" if successful else "needs-attention"
    return {"subscription_id": subscription_id, "state": state}
''',
    "src/entitlements/grant_service.py": '''from __future__ import annotations


def activate_entitlements(subscription_id: str, features: list[str]) -> tuple[str, ...]:
    if not subscription_id:
        raise ValueError("subscription id is required")
    return tuple(sorted(set(features)))
''',
    "src/accounts/tenant_access_policy.py": '''from __future__ import annotations


def may_manage_subscription(actor_tenant: str, subscription_tenant: str, role: str) -> bool:
    return actor_tenant == subscription_tenant and role in {"owner", "billing-admin"}
''',
    "config/billing.yaml": "billing:\n  gateway_timeout_seconds: 8\n  retry_limit: 3\n  idempotency_scope: subscription-cycle\n",
    "config/workers.toml": "[renewals]\nbatch_size = 100\nmax_concurrency = 8\n",
    "schemas/subscription-event.json": json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["subscription_id", "cycle", "event_type"],
            "properties": {
                "subscription_id": {"type": "string"},
                "cycle": {"type": "string"},
                "event_type": {"enum": ["renewed", "failed", "cancelled"]},
            },
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    "legacy/billing/renewal_processor.py": '''"""Deprecated batch renewal calculation retained for archived invoices."""


def summarize_legacy_renewals(invoice_ids: list[str]) -> int:
    return len(set(invoice_ids))
''',
}


def _identifier(*parts: str) -> str:
    return "_".join(part.replace("-", "_") for part in parts)


def _module_source(subsystem: str, entity: str, role: str, ordinal: int) -> str:
    identifier = _identifier(subsystem, entity, role)
    shape = ordinal % 7
    if role == "model":
        return (
            "from __future__ import annotations\n\n"
            "from dataclasses import dataclass\n\n\n"
            "@dataclass(frozen=True)\n"
            f"class {''.join(part.title() for part in identifier.split('_'))}:\n"
            "    key: str\n"
            "    revision: int = 1\n\n"
            "    def stable_identity(self) -> str:\n"
            f"        return f\"{subsystem}:{entity}:{{self.key}}:{{self.revision}}\"\n"
        )
    if role == "repository":
        return (
            "from __future__ import annotations\n\n\n"
            f"class {''.join(part.title() for part in identifier.split('_'))}:\n"
            "    def __init__(self) -> None:\n"
            "        self._rows: dict[str, dict[str, object]] = {}\n\n"
            "    def store(self, key: str, payload: dict[str, object]) -> None:\n"
            "        self._rows[key] = dict(payload)\n\n"
            "    def fetch(self, key: str) -> dict[str, object] | None:\n"
            "        row = self._rows.get(key)\n"
            "        return dict(row) if row is not None else None\n"
        )
    if role == "policy":
        comparator = ">=" if shape % 2 else ">"
        return (
            "from __future__ import annotations\n\n\n"
            f"def permits_{entity}(current: int, threshold: int, *, enabled: bool = True) -> bool:\n"
            f"    \"\"\"Evaluate the {subsystem} {entity} policy at its owned boundary.\"\"\"\n"
            "    if not enabled:\n"
            "        return False\n"
            f"    return current {comparator} threshold\n"
        )
    if role == "handler":
        return (
            "from __future__ import annotations\n\n\n"
            f"def handle_{entity}(payload: dict[str, object]) -> dict[str, object]:\n"
            f"    \"\"\"Normalize one {subsystem} {entity} boundary payload.\"\"\"\n"
            "    result = dict(payload)\n"
            f"    result[\"handled_by\"] = \"{identifier}\"\n"
            f"    result[\"shape\"] = {shape}\n"
            "    return result\n"
        )
    branch = "value.strip()" if shape % 3 else "value.strip().casefold()"
    return (
        "from __future__ import annotations\n\n\n"
        f"def process_{entity}(value: str, *, active: bool = True) -> str:\n"
        f"    \"\"\"Process {subsystem} {entity} values for the application layer.\"\"\"\n"
        "    if not active:\n"
        "        return value\n"
        f"    normalized = {branch}\n"
        f"    return f\"{subsystem}:{entity}:{{normalized}}\"\n"
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _base_files(root: Path, title: str) -> None:
    _write(root / ".gitignore", ".agent/\n.cache/\nbuild/\n__pycache__/\n")
    _write(root / ".codebase-knowledge.toml", "include_untracked = false\n")
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\naddopts = '-q'\ntestpaths = ['tests']\n")
    _write(
        root / "README.md",
        f"# {title}\n\nSynthetic production-shaped repository used for offline navigation evaluation.\n",
    )
    _write(root / "src" / "__init__.py", "")


def _generate_repository(
    root: Path,
    *,
    title: str,
    model: dict[str, list[str]],
    roles: tuple[str, ...],
    core: dict[str, str],
) -> None:
    _base_files(root, title)
    ordinal = 0
    for subsystem, entities in model.items():
        _write(root / "src" / subsystem / "__init__.py", "")
        for entity in entities:
            for role in roles:
                relative = f"src/{subsystem}/{entity}_{role}.py"
                _write(root / relative, _module_source(subsystem, entity, role, ordinal))
                ordinal += 1
        _write(
            root / "tests" / "unit" / f"test_{subsystem}_contracts.py",
            "from pathlib import Path\n\n\n"
            f"def test_{subsystem}_modules_are_present() -> None:\n"
            f"    assert len(list(Path('src/{subsystem}').glob('*.py'))) >= {len(entities) * len(roles)}\n",
        )
        _write(
            root / "docs" / f"{subsystem}.md",
            f"# {subsystem.title()}\n\nThe {subsystem} subsystem owns its application and persistence boundaries.\n",
        )
    for relative, text in core.items():
        _write(root / relative, text)
    for index, subsystem in enumerate(model):
        _write(
            root / "migrations" / f"{20240101 + index}_{subsystem}_state.sql",
            f"CREATE TABLE {subsystem}_state (\n"
            "    key TEXT PRIMARY KEY,\n"
            "    revision INTEGER NOT NULL,\n"
            "    payload TEXT NOT NULL\n"
            ");\n",
        )
        _write(
            root / "config" / f"{subsystem}.json",
            json.dumps(
                {"service": subsystem, "timeout_seconds": 5 + index, "enabled": True},
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
    _write(
        root / "tests" / "integration" / "test_configuration_inventory.py",
        "from pathlib import Path\n\n\n"
        "def test_every_service_has_configuration() -> None:\n"
        "    assert list(Path('config').glob('*'))\n",
    )
    _write(
        root / "tests" / "contract" / "test_schema_inventory.py",
        "from pathlib import Path\n\n\n"
        "def test_contract_schemas_are_committed() -> None:\n"
        "    assert list(Path('schemas').glob('*.json'))\n",
    )
    for index, entity in enumerate(sorted({item for values in model.values() for item in values})):
        _write(
            root / "generated" / "typescript" / f"{entity}.ts",
            f"// Generated from committed domain metadata for {entity}.\n"
            f"export interface {entity.title().replace('_', '')}Record {{ key: string; revision: number; kind: '{entity}'; }}\n",
        )
        if index % 4 == 0:
            _write(
                root / "scripts" / f"verify_{entity}.py",
                "from pathlib import Path\n\n"
                f"assert Path('generated/typescript/{entity}.ts').is_file()\n",
            )
    _write(
        root / "docs" / "operations.md",
        "# Operations\n\nWorkers use bounded concurrency and emit structured retry diagnostics.\n",
    )
    _write(
        root / "docs" / "legacy-notes.md",
        "# Legacy notes\n\nSome names describe retired batch paths and are not current ownership evidence.\n",
    )


def generate_all(destination: Path) -> None:
    print("[fixtures] generating flag-control-plane", flush=True)
    print("[fixtures] generating subscription-platform", flush=True)
    _generate_repository(
        destination / "flag-control-plane",
        title="Flag Control Plane",
        model=FEATURE_MODEL,
        roles=FEATURE_ROLES,
        core=FEATURE_CORE,
    )
    _generate_repository(
        destination / "subscription-platform",
        title="Subscription Platform",
        model=SUBSCRIPTION_MODEL,
        roles=SUBSCRIPTION_ROLES,
        core=SUBSCRIPTION_CORE,
    )
    for fixture_id in ("schema-migration-service", "plugin-workspace", "component-pipeline", "resolver-scale-stress"):
        print(f"[fixtures] generating {fixture_id}", flush=True)
        generate_realistic_fixture(fixture_id, destination / fixture_id)


def generate_fixture(fixture_id: str, destination: Path) -> None:
    """Generate one deterministic comparative fixture into an empty directory."""
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"fixture output must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    if fixture_id in {"schema-migration-service", "plugin-workspace", "component-pipeline", "resolver-scale-stress"}:
        # The archetype emitter performs the same empty-root safety check.
        destination.rmdir()
        generate_realistic_fixture(fixture_id, destination)
        return
    if fixture_id == "flag-control-plane":
        _generate_repository(
            destination,
            title="Flag Control Plane",
            model=FEATURE_MODEL,
            roles=FEATURE_ROLES,
            core=FEATURE_CORE,
        )
        return
    if fixture_id == "subscription-platform":
        _generate_repository(
            destination,
            title="Subscription Platform",
            model=SUBSCRIPTION_MODEL,
            roles=SUBSCRIPTION_ROLES,
            core=SUBSCRIPTION_CORE,
        )
        return
    raise ValueError(f"unknown generated fixture: {fixture_id}")


def _tree(root: Path) -> FixtureTree:
    return inspect_fixture_tree(root)


def _remove_tree(root: Path, *, attempts: int = 12) -> None:
    """Remove a generated tree despite short-lived Windows sync/indexer races."""
    for attempt in range(attempts):
        if not root.exists():
            return
        try:
            shutil.rmtree(root)
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.25 * (attempt + 1))
    if root.exists():
        raise OSError(f"generated tree still exists after removal: {root}")


def _progress(session: Path, event: str, **details: object) -> None:
    """Append bounded, machine-readable regeneration progress outside Git."""
    payload = {"event": event, "at": round(time.time(), 3), **details}
    with (session / "progress.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    print(f"[fixtures] {event}" + (f" {details}" if details else ""), flush=True)


def _retry_file(action: str, operation: object, session: Path, relative: str) -> None:
    """Run one locked-file operation with deterministic bounded retries."""
    for attempt in range(12):
        try:
            operation()  # type: ignore[operator]
            return
        except OSError as exc:
            if attempt == 11:
                raise
            _progress(session, "retry", action=action, path=relative, attempt=attempt + 1, error=str(exc))
            time.sleep(0.25 * (attempt + 1))


def _write_changed_file(source: Path, target: Path, session: Path, relative: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.map-codebase-{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source, temporary)
    _retry_file("replace", lambda: os.replace(temporary, target), session, relative)


def _sync_fixture(generated: Path, canonical: Path, journal: Path, session: Path) -> None:
    """Synchronize one verified fixture without replacing or deleting its root.

    Every overwritten or removed file is copied into the scratch journal first.
    A later verification failure can therefore restore the exact prior tree.
    """
    expected = {
        path.relative_to(generated).as_posix(): path
        for path in generated.rglob("*") if path.is_file()
    }
    existing = {
        path.relative_to(canonical).as_posix(): path
        for path in canonical.rglob("*") if path.is_file()
    } if canonical.exists() else {}
    backup = journal / canonical.name / "backup"
    changed = sorted(relative for relative, source in expected.items() if relative in existing and source.read_bytes() != existing[relative].read_bytes())
    created = sorted(set(expected) - set(existing))
    removed = sorted(set(existing) - set(expected))
    operations = journal / canonical.name / "operations.json"
    operations.parent.mkdir(parents=True, exist_ok=True)
    operations.write_text(json.dumps({"changed": changed, "created": created, "removed": removed}, sort_keys=True), encoding="utf-8")
    try:
        for relative in changed + created:
            source = expected[relative]
            target = canonical / relative
            if relative in changed:
                backup_path = backup / relative
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, backup_path)
            _write_changed_file(source, target, session, relative)
        for relative in removed:
            target = existing[relative]
            backup_path = backup / relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, backup_path)
            _retry_file("remove", target.unlink, session, relative)
    except Exception:
        _rollback_fixture(canonical, journal, session)
        raise
    _progress(session, "synchronized", fixture=canonical.name, changed=len(changed), created=len(created), removed=len(removed))


def _rollback_fixture(canonical: Path, journal: Path, session: Path) -> None:
    operations = journal / canonical.name / "operations.json"
    if not operations.is_file():
        return
    data = json.loads(operations.read_text(encoding="utf-8"))
    backup = journal / canonical.name / "backup"
    for relative in sorted([*data.get("changed", []), *data.get("removed", [])]):
        _write_changed_file(backup / relative, canonical / relative, session, relative)
    for relative in sorted(data.get("created", [])):
        target = canonical / relative
        if target.exists():
            _retry_file("rollback-remove", target.unlink, session, relative)
    _progress(session, "rolled-back", fixture=canonical.name)


def _sync_generated_repositories(generated: Path, session: Path) -> None:
    journal = session / "journal"
    completed: list[Path] = []
    try:
        for fixture in sorted(path for path in generated.iterdir() if path.is_dir()):
            canonical = REPOS / fixture.name
            _progress(session, "synchronizing", fixture=fixture.name)
            _sync_fixture(fixture, canonical, journal, session)
            if _tree(fixture) != _tree(canonical):
                raise RuntimeError(f"post-sync digest mismatch for {fixture.name}")
            completed.append(canonical)
        _progress(session, "verified-sync", fixtures=len(completed))
    except Exception:
        for canonical in reversed(completed):
            _rollback_fixture(canonical, journal, session)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--keep-on-failure", action="store_true", help="retain the scratch session for local diagnosis")
    parser.add_argument("--fixture", choices=("flag-control-plane", "subscription-platform", "schema-migration-service", "plugin-workspace", "component-pipeline", "resolver-scale-stress"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output:
        if not args.fixture:
            parser.error("--output requires --fixture")
        if not args.write:
            parser.error("--output requires --write")
        generate_fixture(args.fixture, args.output)
        print(args.output)
        return 0
    if args.fixture:
        canonical = REPOS / args.fixture
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        session = Path(tempfile.mkdtemp(prefix=f"fixture-{args.fixture}-", dir=SCRATCH_ROOT))
        failed = True
        try:
            generated = session / "generated" / args.fixture
            _progress(session, "generating", fixture=args.fixture)
            generate_fixture(args.fixture, generated)
            if args.check:
                if not canonical.is_dir() or _tree(generated) != _tree(canonical):
                    print(f"Generated fixture {args.fixture} differs from committed output.")
                    return 1
                print(f"Generated fixture {args.fixture} is byte-identical.")
                return 0
            _sync_generated_repositories(generated.parent, session)
            failed = False
            print(f"Generated benchmark fixture {args.fixture}.")
            return 0
        finally:
            if not failed or not args.keep_on_failure:
                _remove_tree(session)
            else:
                print(f"Fixture generation failed; scratch evidence retained at {session}.", file=sys.stderr)
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="fixture-all-", dir=SCRATCH_ROOT))
    failed = True
    try:
        generated = session / "generated" / "repos"
        _progress(session, "generating-all")
        generate_all(generated)
        if args.check:
            if not REPOS.is_dir() or _tree(generated) != _tree(REPOS):
                print("Generated fixture repositories differ from committed output.")
                return 1
            print("Generated fixture repositories are byte-identical.")
            return 0
        resolved = REPOS.resolve()
        if resolved != (ROOT / "benchmarks" / "repos").resolve():
            raise RuntimeError(f"refusing unexpected output root: {resolved}")
        REPOS.mkdir(parents=True, exist_ok=True)
        _sync_generated_repositories(generated, session)
        failed = False
        print("Generated benchmark fixture repositories.")
        return 0
    finally:
        if not failed or not args.keep_on_failure:
            _remove_tree(session)
        else:
            print(f"Fixture generation failed; scratch evidence retained at {session}.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
