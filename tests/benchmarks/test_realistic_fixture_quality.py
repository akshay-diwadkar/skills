"""Structural realism gates for the committed map-codebase reference fixtures."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from benchmarks.generators.refresh_v2_manifests import _owner

ROOT = Path(__file__).resolve().parents[2]
REPOS = ROOT / "benchmarks" / "repos"
SOURCE_SUFFIXES = {".py", ".ts", ".go", ".rs", ".java", ".cs"}
FIXTURES = {
    "schema-migration-service": {"files": 30, "loc": 90, "edges": 4, "languages": {".py", ".ts"}},
    "plugin-workspace": {"files": 30, "loc": 90, "edges": 5, "languages": {".ts", ".java"}},
    "component-pipeline": {"files": 30, "loc": 90, "edges": 5, "languages": {".go", ".rs", ".cs"}},
}
COMPOSITION_ROOTS = {
    "schema-migration-service": (
        "services/api/billing_facade.py",
        ("invoice_pricing", "grant_service", "idempotency_store", "outbox_publisher"),
    ),
    "plugin-workspace": (
        "plugins/app.ts",
        ("entity-registration", "permission-router", "template-executor", "catalog-indexer"),
    ),
    "component-pipeline": (
        "go/pipeline/pipeline.go",
        ("receivers", "processors", "shared"),
    ),
}

pytestmark = pytest.mark.fixtures


def _source(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.suffix in SOURCE_SUFFIXES and path.is_file()
        and path.name != "__init__.py"
        and "generated" not in path.parts and "tests" not in path.parts and "scripts" not in path.parts
        and not any(part.casefold() == "shared" for part in path.parts)
    )


def _normalized(path: Path) -> str:
    return re.sub(r"\b\d{1,4}\b", "#", re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).strip())


def _shingles(path: Path, width: int = 5) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\S", path.read_text(encoding="utf-8"))
    return {tuple(tokens[index:index + width]) for index in range(max(1, len(tokens) - width + 1))}


def test_realistic_fixtures_have_substantive_connected_source() -> None:
    for fixture_id, budget in FIXTURES.items():
        root = REPOS / fixture_id
        files = [path for path in root.rglob("*") if path.is_file()]
        source = _source(root)
        contents = {path: path.read_text(encoding="utf-8") for path in source}
        assert len(files) >= budget["files"]
        assert budget["languages"] <= {path.suffix for path in source}
        non_blank_lines = sum(sum(bool(line.strip()) for line in text.splitlines()) for text in contents.values())
        assert non_blank_lines >= budget["loc"]
        assert all(sum(bool(line.strip()) for line in text.splitlines()) >= 3 for text in contents.values())
        edges = sum(len(re.findall(r"(?m)^\s*(?:import|from|use|using)\b", text)) for text in contents.values())
        assert edges >= budget["edges"]


def test_realistic_fixtures_have_reviewable_composition_roots() -> None:
    for fixture_id, (relative_root, dependencies) in COMPOSITION_ROOTS.items():
        content = (REPOS / fixture_id / relative_root).read_text(encoding="utf-8")
        assert all(dependency in content for dependency in dependencies)


def test_realistic_fixtures_reject_template_clone_filler() -> None:
    for fixture_id in FIXTURES:
        source = _source(REPOS / fixture_id)
        normalized = Counter(_normalized(path) for path in source)
        assert max(normalized.values()) <= 2
        assert all("component_" not in path.stem and "module_" not in path.stem for path in source)
        assert all(not re.search(r"_(?:enterprise|growth|startup|public|education|health|retail|media|finance|industrial)_", path.stem) for path in source)
        shingles = [_shingles(path) for path in source]
        nearest = []
        for index, left in enumerate(shingles):
            similarities = [len(left & right) / max(1, len(left | right)) for other, right in enumerate(shingles) if other != index]
            nearest.append(max(similarities, default=0.0))
        nearest.sort()
        assert nearest[max(0, int(len(nearest) * 0.95) - 1)] < 0.85


def test_generated_content_is_bounded_and_tests_execute_behavior() -> None:
    for fixture_id in FIXTURES:
        root = REPOS / fixture_id
        meaningful = [path for path in root.rglob("*") if path.is_file()]
        generated = [path for path in meaningful if "generated" in path.parts]
        assert len(generated) / len(meaningful) < 0.15
        for path in [item for item in meaningful if "test" in item.name.casefold() or "tests" in item.parts]:
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert "content = source.read_text" not in content
            assert "source.is_file" not in content


def test_generated_contracts_have_a_declared_source_of_truth() -> None:
    for fixture_id in FIXTURES:
        root = REPOS / fixture_id
        schema = root / ("schemas/signal.json" if fixture_id == "component-pipeline" else "schemas/change-event.json")
        assert schema.is_file()
        generated = list((root / "generated").rglob("*.ts"))
        assert generated
        assert all("Generated from" in path.read_text(encoding="utf-8") for path in generated)
        tests = [
            path for path in root.rglob("*") if path.is_file()
            and ("test" in path.name.casefold() or any(part.casefold() in {"test", "tests"} for part in path.parts))
            and path.suffix in SOURCE_SUFFIXES
        ]
        assert tests
        assert all("source.is_file" not in path.read_text(encoding="utf-8", errors="ignore") for path in tests)


def test_manifest_oracle_roles_classify_test_directories_and_native_test_names() -> None:
    hashes = {
        "tests/domain/test_invoice_pricing.py": "a" * 64,
        "go/receivers/otlp_receiver_test.go": "b" * 64,
        "policy-service/src/test/java/portal/policy/CatalogRegistrationPolicyTest.java": "c" * 64,
        "services/domain/invoice_pricing.py": "d" * 64,
    }
    assert _owner("tests/domain/test_invoice_pricing.py", hashes)["role"] == "test"
    assert _owner("go/receivers/otlp_receiver_test.go", hashes)["role"] == "test"
    assert _owner(
        "policy-service/src/test/java/portal/policy/CatalogRegistrationPolicyTest.java", hashes
    )["role"] == "test"
    assert _owner("services/domain/invoice_pricing.py", hashes)["role"] == "source"


def test_locked_native_project_surfaces_exist() -> None:
    required = {
        "schema-migration-service": {"pyproject.toml", "requirements.lock", "package-lock.json", "migrations/20250101_create_event_outbox.sql"},
        "plugin-workspace": {"package-lock.json", "gradlew", "gradle/wrapper/gradle-wrapper.properties", "policy-service/build.gradle"},
        "component-pipeline": {"go.mod", "go.sum", "Cargo.lock", "dotnet/exporter/packages.lock.json"},
    }
    for fixture_id, paths in required.items():
        assert all((REPOS / fixture_id / path).is_file() for path in paths)

    billing = REPOS / "schema-migration-service"
    requirements = (billing / "requirements.lock").read_text(encoding="utf-8")
    assert "--hash=sha256:" in requirements
    assert "fastapi==0.115.6" in requirements and "sqlalchemy==2.0.36" in requirements
    for fixture_id in ("schema-migration-service", "plugin-workspace"):
        package_lock = (REPOS / fixture_id / "package-lock.json").read_text(encoding="utf-8")
        assert '"node_modules/typescript"' in package_lock
        assert '"integrity": "sha512-' in package_lock

    portal = REPOS / "plugin-workspace"
    assert (portal / "gradle/wrapper/gradle-wrapper.jar").stat().st_size > 40_000
    wrapper = (portal / "gradle/wrapper/gradle-wrapper.properties").read_text(encoding="utf-8")
    assert "distributionSha256Sum=" in wrapper and "networkTimeout=300000" in wrapper
    assert "org.junit.jupiter:junit-jupiter:5.11.4" in (portal / "policy-service/gradle.lockfile").read_text(encoding="utf-8")
    assert "<sha256 value=" in (portal / "gradle/verification-metadata.xml").read_text(encoding="utf-8")

    telemetry = REPOS / "component-pipeline"
    rust_library = (telemetry / "rust/transform/src/lib.rs").read_text(encoding="utf-8")
    assert rust_library.count("pub mod ") >= 2
    assert (telemetry / "dotnet/verification/packages.lock.json").is_file()
