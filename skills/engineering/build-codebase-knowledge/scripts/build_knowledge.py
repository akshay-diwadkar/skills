#!/usr/bin/env python3
"""Build codebase knowledge artifacts: context.md, architecture.md, index.json, manifest.json."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from link_agent_docs import link_agent_docs

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

DEFAULT_CONFIG = {
    "output_dir": ".agent/knowledge",
    "max_context_lines": 120,
    "max_architecture_lines": 220,
    "max_summary_words": 12,
    "full_refresh_change_ratio": 0.20,
    "include": ["src/**", "lib/**", "app/**", "pkg/**", "tests/**", "config/**"],
    "exclude": [
        "**/node_modules/**",
        "**/vendor/**",
        "**/dist/**",
        "**/build/**",
        "**/.git/**",
        "**/.agent/**",
        "**/__pycache__/**",
        "**/*.min.js",
        "**/*.pyc",
        "**/.venv/**",
        "**/venv/**",
    ],
    "generated": ["**/generated/**", "**/*.gen.*"],
    "weights": {
        "exact_symbol": 10.0,
        "exact_path": 10.0,
        "filename": 7.0,
        "subsystem": 5.0,
        "entry_point": 5.0,
        "dependency_neighbor": 3.0,
        "related_test": 4.0,
        "configuration": 4.0,
        "text_match": 2.0,
        "generated_penalty": -8.0,
        "vendor_penalty": -10.0,
    },
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api_key|secret|password|private_key|auth_token|bearer)\s*=\s*['\"]?[a-zA-Z0-9_\-\.]{8,}"),
    re.compile(r"-----BEGIN (PRIVATE KEY|RSA PRIVATE KEY)-----"),
]

def load_config(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / ".codebase-knowledge.toml"
    config = dict(DEFAULT_CONFIG)
    if config_path.is_file() and tomllib:
        try:
            with config_path.open("rb") as f:
                data = tomllib.load(f)
                config.update(data)
        except Exception:
            pass
    return config

def compute_file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
        return h.hexdigest()[:16]
    except Exception:
        return ""

def get_git_info(repo_root: Path) -> tuple[str, str, bool]:
    revision = "unknown"
    branch = "unknown"
    dirty = False
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=False
        )
        if rev.returncode == 0:
            revision = rev.stdout.strip()

        br = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=False
        )
        if br.returncode == 0:
            branch = br.stdout.strip()

        st = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root, capture_output=True, text=True, check=False
        )
        if st.returncode == 0 and st.stdout.strip():
            dirty = True
    except Exception:
        pass
    return revision, branch, dirty

def is_secret_file_or_content(path: Path, content: str) -> bool:
    if path.name.startswith(".env") and not path.name.endswith(".example"):
        return True
    if any(k in path.name.lower() for k in ["id_rsa", "credentials", "secret", "private_key"]):
        return True
    for p in SECRET_PATTERNS:
        if p.search(content):
            return True
    return False

def matches_glob(rel_path_str: str, patterns: list[str]) -> bool:
    norm_path = rel_path_str.replace("\\", "/").strip("/")
    parts = norm_path.split("/")
    for pat in patterns:
        pat_norm = pat.replace("\\", "/").strip("/")
        # Check segment match (e.g. vendor, node_modules, dist, __pycache__)
        segments = [p.strip("/") for p in pat_norm.split("/") if p and p != "**"]
        if len(segments) == 1 and segments[0] in parts:
            return True
        regex = "^" + pat_norm.replace(".", r"\.").replace("**/", r"(?:.*/)?").replace("/**", r"(?:/.*)?").replace("*", r"[^/]*").replace("?", r".") + "$"
        if re.match(regex, norm_path):
            return True
    return False

class CodeExtractor:
    def __init__(self, repo_root: Path, config: dict[str, Any]):
        self.repo_root = repo_root
        self.config = config
        self.files: list[dict[str, Any]] = []
        self.symbols: list[dict[str, Any]] = []
        self.subsystems: dict[str, list[str]] = {}
        self.entry_points: list[dict[str, Any]] = []
        self.dependencies: list[dict[str, Any]] = []
        self.tests: list[dict[str, Any]] = []
        self.configurations: list[dict[str, Any]] = []
        self.generated_paths: list[str] = []
        self.ignored_paths: list[str] = []
        self.file_hashes: dict[str, str] = {}
        self.languages: set[str] = set()
        self.frameworks: set[str] = set()

    def discover_and_extract(self) -> None:
        for root, dirs, filenames in os.walk(self.repo_root):
            # Prune excluded dirs
            rel_root = Path(root).relative_to(self.repo_root)
            dirs[:] = [
                d for d in dirs
                if not matches_glob(str((rel_root / d)), self.config["exclude"])
                and not d.startswith(".")
            ]

            for fname in filenames:
                full_path = Path(root) / fname
                rel_path = full_path.relative_to(self.repo_root)
                rel_str = str(rel_path).replace("\\", "/")

                if matches_glob(rel_str, self.config["exclude"]):
                    self.ignored_paths.append(rel_str)
                    continue

                if matches_glob(rel_str, self.config["generated"]):
                    self.generated_paths.append(rel_str)

                self.process_file(full_path, rel_str)

    def process_file(self, full_path: Path, rel_str: str) -> None:
        file_hash = compute_file_hash(full_path)
        self.file_hashes[rel_str] = file_hash

        suffix = full_path.suffix.lower()
        content = ""
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        if is_secret_file_or_content(full_path, content):
            self.ignored_paths.append(rel_str)
            return

        # Language detection
        lang = self.detect_language(suffix, rel_str)
        if lang:
            self.languages.add(lang)

        # Subsystem assignment
        subsystem = self.assign_subsystem(rel_str)
        if subsystem not in self.subsystems:
            self.subsystems[subsystem] = []
        self.subsystems[subsystem].append(rel_str)

        # Config detection
        if suffix in [".toml", ".yaml", ".yml", ".json", ".ini"] or rel_str.endswith(".env.example"):
            self.configurations.append({"path": rel_str, "role": "configuration"})

        # Role & symbol extraction
        role = "source"
        file_symbols: list[str] = []
        file_imports: list[str] = []

        if "test" in rel_str.lower() or suffix == ".py" and full_path.name.startswith("test_"):
            role = "test"
            target_source = rel_str.replace("tests/", "src/").replace("test_", "").replace("_test", "")
            self.tests.append({"path": rel_str, "targets": [target_source]})

        if suffix == ".py":
            file_symbols, file_imports = self.parse_python(full_path, rel_str, content, subsystem)
        elif suffix in [".js", ".ts", ".jsx", ".tsx"]:
            file_symbols, file_imports = self.parse_js_ts(rel_str, content, subsystem)
        elif suffix in [".go", ".rs"]:
            file_symbols, file_imports = self.parse_lexical(rel_str, content, subsystem)

        # Entry point detection
        if self.is_entry_point(rel_str, content, file_symbols):
            self.entry_points.append({
                "name": rel_str,
                "path": rel_str,
                "symbol": file_symbols[0] if file_symbols else "main",
                "kind": "entry-point"
            })

        keywords = list(set([subsystem, role] + file_symbols[:5] + [Path(rel_str).stem]))

        self.files.append({
            "path": rel_str,
            "subsystem": subsystem,
            "role": role,
            "symbols": file_symbols,
            "imports": file_imports,
            "imported_by": [],
            "tests": [t["path"] for t in self.tests if rel_str in t.get("targets", [])],
            "keywords": keywords,
            "hash": file_hash,
            "role_summary": f"{role.capitalize()} module in {subsystem} subsystem."
        })

    def detect_language(self, suffix: str, rel_str: str) -> str:
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
        }
        return mapping.get(suffix, "")

    def assign_subsystem(self, rel_str: str) -> str:
        parts = rel_str.split("/")
        if len(parts) > 1:
            if parts[0] in ["src", "lib", "app", "pkg"] and len(parts) > 2:
                return parts[1]
            return parts[0]
        return "root"

    def is_entry_point(self, rel_str: str, content: str, symbols: list[str]) -> bool:
        lower = rel_str.lower()
        if any(e in lower for e in ["main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py", "main.go", "main.rs"]):
            return True
        if "if __name__ == '__main__':" in content or "create_app" in content or "def main(" in content:
            return True
        return False

    def parse_python(self, full_path: Path, rel_str: str, content: str, subsystem: str) -> tuple[list[str], list[str]]:
        symbols = []
        imports = []
        try:
            tree = ast.parse(content, filename=str(full_path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    symbols.append(name)
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    self.symbols.append({
                        "name": name,
                        "qualified_name": f"{Path(rel_str).stem}.{name}",
                        "kind": kind,
                        "path": rel_str,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                        "subsystem": subsystem,
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except Exception:
            pass
        return symbols, imports

    def parse_js_ts(self, rel_str: str, content: str, subsystem: str) -> tuple[list[str], list[str]]:
        symbols = re.findall(r"(?:export\s+)?(?:function|class|const|let|var)\s+([a-zA-Z0-9_]+)", content)
        imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)
        for s in symbols[:20]:
            self.symbols.append({
                "name": s,
                "qualified_name": f"{Path(rel_str).stem}.{s}",
                "kind": "exported-symbol",
                "path": rel_str,
                "line_start": 1,
                "line_end": 1,
                "subsystem": subsystem
            })
        return symbols, imports

    def parse_lexical(self, rel_str: str, content: str, subsystem: str) -> tuple[list[str], list[str]]:
        symbols = re.findall(r"(?:fn|func|type|struct)\s+([a-zA-Z0-9_]+)", content)
        imports = re.findall(r"import\s+(?:\([^\)]+\)|[^\n]+)", content)
        for s in symbols[:20]:
            self.symbols.append({
                "name": s,
                "qualified_name": f"{Path(rel_str).stem}.{s}",
                "kind": "symbol",
                "path": rel_str,
                "line_start": 1,
                "line_end": 1,
                "subsystem": subsystem
            })
        return symbols, imports

def build_knowledge(repo_root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    config = load_config(repo_root)
    out_dir = output_dir if output_dir else repo_root / config["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    extractor = CodeExtractor(repo_root, config)
    extractor.discover_and_extract()

    revision, branch, dirty = get_git_info(repo_root)

    index_data = {
        "schema_version": "1.0",
        "repository": {
            "root": ".",
            "revision": revision,
            "languages": sorted(list(extractor.languages)),
            "frameworks": sorted(list(extractor.frameworks)),
        },
        "subsystems": [
            {"name": k, "paths": v, "description": f"{k.capitalize()} subsystem."}
            for k, v in extractor.subsystems.items()
        ],
        "files": extractor.files,
        "symbols": extractor.symbols,
        "entry_points": extractor.entry_points,
        "flows": [
            {"name": "Main Execution Flow", "kind": "entry", "steps": [ep["path"] for ep in extractor.entry_points]}
        ],
        "dependencies": extractor.dependencies,
        "tests": extractor.tests,
        "configurations": extractor.configurations,
        "generated_paths": extractor.generated_paths,
        "ignored_paths": extractor.ignored_paths,
    }

    # Format context.md
    context_lines = [
        "# Repository Context",
        "",
        "Status: fresh",
        f"Revision: {revision}",
        "Source truth: repository files",
        "",
        "## Purpose",
        f"- Repository providing functionality across {len(extractor.subsystems)} subsystem(s).",
        "",
        "## Stack",
        "\n".join(f"- {lang}" for lang in sorted(list(extractor.languages))) if extractor.languages else "- Standard Codebase",
        "",
        "## Components",
        "\n".join(f"- {k}: `{v[0]}` ({len(v)} files)" for k, v in extractor.subsystems.items()),
        "",
        "## Entry Points",
        "\n".join(f"- {ep['kind'].capitalize()}: `{ep['path']}:{ep['symbol']}`" for ep in extractor.entry_points[:5]) if extractor.entry_points else "- Entry point: `main.py`",
        "",
        "## Commands",
        "- Test: `pytest`",
        "- Lint: `ruff check .`",
        "",
        "## Critical Boundaries",
        "- Domain logic encapsulated in source modules",
        "- Storage / external integrations decoupled via interfaces",
        "",
        "## Ignore First",
        "- `vendor/`",
        "- `dist/`",
        "- `node_modules/`",
        "",
        "## More Detail",
        "- Architecture: `architecture.md`",
        "- Machine index: `index.json`",
    ]
    context_content = "\n".join(context_lines) + "\n"

    # Format architecture.md
    arch_lines = [
        "# Architecture",
        "",
        "Status: fresh",
        f"Revision: {revision}",
        "",
        "## Boundaries",
        "",
        "| Component | Paths | Owns | Depends On |",
        "|---|---|---|---|",
    ]
    for sub, paths in extractor.subsystems.items():
        sample_path = paths[0] if paths else sub
        arch_lines.append(f"| {sub.capitalize()} | `{sample_path}` | Subsystem operations | Domain |")

    arch_lines.extend([
        "",
        "## Dependency Rules",
        "- High-level modules should not depend on low-level details.",
        "- Tests import source modules directly.",
        "",
        "## Runtime Flow",
        "1. Entry point triggers execution.",
        "2. Subsystem modules process requests.",
        "3. Persistence / adapters handle state.",
        "",
        "## Auth & Storage",
        "- Configurations: mapped via config files.",
        "",
        "## Test Layout",
        "- Source-to-test convention mapped in `index.json`.",
        "",
        "## Known Risks",
        "- Ensure incremental updates on source edits.",
        "",
        "## Unknown",
        "- Dynamic runtime reflection dependencies.",
    ])
    architecture_content = "\n".join(arch_lines) + "\n"

    manifest_data = {
        "schema_version": "1.0",
        "generator_version": "1.0.0",
        "repository": {
            "root": ".",
            "revision": revision,
            "branch": branch,
            "dirty": dirty,
        },
        "generation_mode": "full",
        "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16],
        "indexed_paths": [f["path"] for f in extractor.files],
        "ignored_paths": extractor.ignored_paths,
        "changed_files": [],
        "file_hashes": extractor.file_hashes,
        "freshness_state": "fresh",
    }

    # Write files
    (out_dir / "index.json").write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    (out_dir / "context.md").write_text(context_content, encoding="utf-8")
    (out_dir / "architecture.md").write_text(architecture_content, encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Link knowledge docs in AGENTS.md / CLAUDE.md
    link_agent_docs(repo_root, out_dir)

    return {
        "status": "success",
        "output_dir": str(out_dir),
        "files_indexed": len(extractor.files),
        "symbols_indexed": len(extractor.symbols),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Build codebase knowledge artifacts.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Output directory for knowledge artifacts")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.output).resolve() if args.output else None

    res = build_knowledge(repo_root, out_dir)
    if not args.quiet:
        print(f"Build completed: {res['files_indexed']} files, {res['symbols_indexed']} symbols indexed -> {res['output_dir']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
