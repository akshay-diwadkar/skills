from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

import validate_repository as validator  # noqa: E402

INVENTORY = Path(__file__).with_name("mandatory_skill_rules.json")
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^)\s]+))")


def _skill_dirs(root: Path) -> dict[str, Path]:
    return {path.name: path for path in (root / "skills").glob("*/*") if (path / "SKILL.md").is_file()}


def _phase_roots(skill: Path, surface: str) -> set[Path]:
    if surface == "doctor":
        return {(skill / "SKILL.md").resolve()}
    manifest = json.loads((skill / "skill-protocol.json").read_text(encoding="utf-8"))
    phase = manifest["phases"][surface]
    templates = list(phase["required_reads"])
    for conditional in phase.get("conditional_reads", []):
        templates.extend(conditional["paths"])
    roots = set()
    for template in templates:
        prefix = "{skill_dir}/"
        if template.startswith(prefix):
            roots.add((skill / template[len(prefix) :]).resolve())
    return roots


def _reachable_markdown(roots: set[Path], skill: Path) -> set[Path]:
    reachable = set(roots)
    pending = list(roots)
    while pending:
        source = pending.pop()
        if source.suffix != ".md" or not source.is_file():
            continue
        for match in LINK_RE.finditer(source.read_text(encoding="utf-8")):
            target_text = match.group(1) or match.group(2)
            if target_text.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = (source.parent / target_text.split("#", 1)[0]).resolve()
            if target.is_relative_to(skill.resolve()) and target not in reachable:
                reachable.add(target)
                pending.append(target)
    return reachable


def inventory_errors(payload: list[dict[str, str]], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    skills = _skill_dirs(root)
    ids = [rule.get("id", "") for rule in payload]
    if len(ids) != len(set(ids)):
        errors.append("rule IDs must be unique")
    covered = {rule.get("skill") for rule in payload}
    if covered != set(skills):
        errors.append("inventory must cover every skill")
    for rule in payload:
        skill = skills.get(rule.get("skill", ""))
        if skill is None:
            errors.append(f"{rule.get('id')}: unknown skill")
            continue
        source = (skill / rule.get("source", "")).resolve()
        if not source.is_file() or not source.is_relative_to(skill.resolve()):
            errors.append(f"{rule.get('id')}: invalid source")
            continue
        if rule.get("text", "") not in source.read_text(encoding="utf-8"):
            errors.append(f"{rule.get('id')}: rule text is missing")
        try:
            roots = _phase_roots(skill, rule.get("surface", ""))
        except (KeyError, json.JSONDecodeError):
            errors.append(f"{rule.get('id')}: invalid required-read surface")
            continue
        if source not in _reachable_markdown(roots, skill):
            errors.append(f"{rule.get('id')}: source is not discoverable from required_reads")
    return errors


def test_every_mandatory_rule_is_discoverable_from_required_reads() -> None:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert inventory_errors(payload) == []


def test_inventory_rejects_duplicate_missing_and_undiscoverable_rules() -> None:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    broken = [dict(rule) for rule in payload]
    broken[0]["id"] = broken[1]["id"]
    broken[1]["text"] = "missing mandatory text"
    next(rule for rule in broken if rule["id"] == "design.one-artifact")["surface"] = "validated"
    errors = inventory_errors(broken)
    assert "rule IDs must be unique" in errors
    assert any("rule text is missing" in error for error in errors)
    assert any("source is not discoverable" in error for error in errors)


def test_markdown_reference_validation_rejects_missing_escape_and_orphan(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    skill = tmp_path / "skills" / "engineering" / "fixture"
    references = skill / "references"
    references.mkdir(parents=True)
    (references / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
    (skill / "SKILL.md").write_text(
        "[missing](references/missing.md)\n[escape](../../../../outside.md)\n",
        encoding="utf-8",
    )
    errors = validator.validate_markdown_references(skill)
    assert any("does not exist" in error for error in errors)
    assert any("escapes the repository" in error for error in errors)
    assert any("reference is not linked directly" in error for error in errors)


def test_context_load_report_is_current() -> None:
    assert validator.validate_context_load_report() == []


def test_context_load_report_rejects_stale_metrics(tmp_path: Path) -> None:
    report_path = ROOT / "benchmarks" / "reports" / "context-load.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["skills"]["manualize"]["metrics"]["top_level"] += 1
    stale = tmp_path / "context-load.json"
    stale.write_text(json.dumps(report), encoding="utf-8")
    assert any("generated report is stale" in error for error in validator.validate_context_load_report(stale))
