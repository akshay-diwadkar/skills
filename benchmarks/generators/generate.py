#!/usr/bin/env python3
"""Generate the committed synthetic benchmark repositories from fixed domain models."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = ROOT / "benchmarks" / "repos"

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


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="benchmark-generate-") as temporary:
        generated = Path(temporary) / "repos"
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
        if REPOS.exists():
            shutil.rmtree(REPOS)
        shutil.copytree(generated, REPOS)
    print("Generated benchmark fixture repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
