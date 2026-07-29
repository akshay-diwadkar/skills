from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "technical-communication" / "manualize" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def manual_case(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "source.txt"
    source.write_text("The service starts with port 8080.\n", encoding="utf-8")
    manual = tmp_path / "manual.md"
    manual.write_text("# Procedure\n\nRun the service.\n", encoding="utf-8")
    bundle = {
        "contract_version": "manualize-1",
        "operation": "write",
        "document": "procedure",
        "risk": "low",
        "profile": "strict",
        "glossary": {
            "terms": [],
            "abbreviations": {},
            "action_verbs": [],
            "phrasal_verbs": [],
            "hazardous_actions": [],
        },
        "sources": [
            {
                "id": "SRC-1",
                "path": "source.txt",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "authority": "service contract",
            }
        ],
        "required_facts": [],
        "integrity_literals": [],
        "procedures": [],
        "warnings": [],
        "recovery_steps": [],
        "prerequisites": [],
        "branches": [],
    }
    bundle_path = tmp_path / "manual-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return repo, manual, bundle_path, bundle
