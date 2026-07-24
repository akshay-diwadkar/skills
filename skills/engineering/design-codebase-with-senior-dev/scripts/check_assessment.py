#!/usr/bin/env python3
"""Check a design-codebase-with-senior-dev assessment artifact against Contract v2."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import (  # noqa: E402
    GIT_HISTORY_LOCATOR_RE,
    HARD_PATTERN_QUESTIONS,
    VALID_DEBT_DISPOSITIONS,
    VALID_DEBT_TYPES,
    VALID_FRESHNESS,
    VALID_HANDOFFS,
    VALID_SOURCES,
    VALID_STRENGTHS,
    AlternativeRecord,
    Assessment,
    AssumptionRecord,
    ContractRecord,
    DecisionRecord,
    DecisionSummary,
    Diagnostic,
    ExternalFactRecord,
    FactRecord,
    HandoffRecord,
    MigrationRecord,
    PatternGateRecord,
    PressureRecord,
    QuestionAnswer,
    ResidualRiskRecord,
    TargetCandidateRecord,
    TechDebtRecord,
    VerificationRecord,
    validate_receipt,
)


def _section(text: str, name: str) -> tuple[str, int | None]:
    match = re.search(
        rf"^## {re.escape(name)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return "", None
    line_number = text[: match.start()].count("\n") + 1
    return match.group("body"), line_number


def _parse_record_kv(line: str) -> tuple[str, dict[str, str]]:
    line_str = line.strip().lstrip("- ").strip()
    if ":" not in line_str:
        return line_str, {}
    rec_id, rest = line_str.split(":", 1)
    rec_id = rec_id.strip()
    parts = [p.strip() for p in rest.split("|") if p.strip()]
    kv: dict[str, str] = {}
    for p in parts:
        if ":" in p:
            k, v = p.split(":", 1)
            kv[k.strip()] = v.strip()
    return rec_id, kv


def parse_assessment(text: str) -> tuple[Assessment, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    assessment = Assessment(raw_text=text)

    # 1. Parse Title
    title_match = re.search(r"^# (?P<title>.+)$", text, re.MULTILINE)
    if title_match:
        assessment.title = title_match.group("title").strip()

    # 2. Parse Marker
    marker_match = re.search(
        r"<!-- design-assessment-contract: (?P<version>\d+); (?:level: (?P<level>L[0-3])|mode: (?P<mode>discovery-only)) -->",
        text,
    )
    if not marker_match:
        diagnostics.append(Diagnostic("contract.marker.missing", "Missing contract marker <!-- design-assessment-contract: 2; level: L0..L3 --> or mode: discovery-only"))
    else:
        version = int(marker_match.group("version"))
        if version != 2:
            diagnostics.append(Diagnostic("contract.version.invalid", f"Contract version must be 2, got {version}"))
        assessment.contract_version = version
        if marker_match.group("mode") == "discovery-only":
            assessment.mode = "discovery-only"
            assessment.level = "discovery-only"
        else:
            assessment.level = marker_match.group("level")

    # 3. Parse Decision Summary
    summary_body, summary_line = _section(text, "Decision Summary")
    if summary_body:
        ds = DecisionSummary()
        for line in summary_body.splitlines():
            line_str = line.strip()
            if line_str.startswith("- Invocation mode:"):
                ds.mode = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Selected target:"):
                ds.target = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Selected level:"):
                ds.level = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Recommended design:"):
                ds.recommendation = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Why minimum sufficient:"):
                ds.why_minimum = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Protected behavior and contracts:"):
                ds.protected_contracts = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Primary structural pressure:"):
                ds.primary_pressure = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Technical-debt disposition:"):
                ds.debt_disposition = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Residual risk:"):
                ds.residual_risk = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("- Next owner:"):
                ds.next_owner = line_str.split(":", 1)[1].strip()
        assessment.decision_summary = ds
        if ds.mode in {"targeted", "autonomous-discovery", "discovery-only"}:
            assessment.mode = ds.mode
    elif assessment.mode != "discovery-only":
        diagnostics.append(Diagnostic("summary.section.missing", "Section ## Decision Summary is required", summary_line))

    # 4. Parse Evidence and Current State (F-n and E-n)
    ev_body, ev_line = _section(text, "Evidence and Current State")
    if ev_body:
        for idx, line in enumerate(ev_body.splitlines(), start=ev_line or 1):
            line_str = line.strip()
            if not line_str.startswith("- "):
                continue

            # F-n parsing: - F-1: `path:1` | anchor: `foo` | observation: bar | source: code | strength: direct | freshness: current
            f_match = re.match(
                r"^-\s*(?P<id>F-\d+):\s*`(?P<path>[^:]+)(?::(?P<line>\d+))?`\s*\|\s*anchor:\s*`(?P<anchor>[^`]*)`\s*\|\s*observation:\s*(?P<obs>.*?)(?:\s*\|\s*source:\s*(?P<source>[^|]+))?(?:\s*\|\s*strength:\s*(?P<strength>[^|]+))?(?:\s*\|\s*freshness:\s*(?P<freshness>[^|]+))?$",
                line_str,
            )
            if f_match:
                assessment.facts.append(
                    FactRecord(
                        id=f_match.group("id"),
                        path=f_match.group("path"),
                        line=int(f_match.group("line")) if f_match.group("line") else 1,
                        anchor=f_match.group("anchor"),
                        observation=f_match.group("obs").strip(),
                        source=(f_match.group("source") or "code").strip(),
                        strength=(f_match.group("strength") or "direct").strip(),
                        freshness=(f_match.group("freshness") or "current").strip().rstrip("."),
                        line_number=idx,
                    )
                )
                continue

            # E-n parsing: - E-1: source: `https://...` | version: `3.11` | claim: foo | freshness: current | relationship: supports | authoritative: true
            e_match = re.match(
                r"^-\s*(?P<id>E-\d+):\s*source:\s*`(?P<source>[^`]*)`\s*\|\s*version:\s*`(?P<ver>[^`]*)`\s*\|\s*claim:\s*(?P<claim>.*?)(?:\s*\|\s*freshness:\s*(?P<freshness>[^|]+))?(?:\s*\|\s*relationship:\s*(?P<rel>[^|]+))?(?:\s*\|\s*authoritative:\s*(?P<auth>[^|]+))?$",
                line_str,
            )
            if e_match:
                assessment.external_facts.append(
                    ExternalFactRecord(
                        id=e_match.group("id"),
                        source_id=e_match.group("source"),
                        version=e_match.group("ver"),
                        claim=e_match.group("claim").strip(),
                        freshness=(e_match.group("freshness") or "current").strip(),
                        relationship=(e_match.group("rel") or "supports").strip(),
                        authoritative=(e_match.group("auth") or "true").strip().lower() == "true",
                        line_number=idx,
                    )
                )

    # 5. Parse Target Discovery Candidates (T-n)
    tdis_body, tdis_line = _section(text, "Target Discovery Candidates")
    if tdis_body:
        for idx, line in enumerate(tdis_body.splitlines(), start=tdis_line or 1):
            line_str = line.strip()
            if not line_str.startswith("- T-"):
                continue
            t_id, kv = _parse_record_kv(line_str)
            if t_id:
                ev_list = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]
                aff_list = [a.strip() for a in kv.get("affected", "").split(",") if a.strip()]
                rank_val = int(kv.get("rank", "1")) if kv.get("rank", "").isdigit() else 1
                intent_req = kv.get("product-intent-required", "false").lower() == "true"
                assessment.discovery_candidates.append(
                    TargetCandidateRecord(
                        id=t_id,
                        target=kv.get("target", "").strip("`"),
                        evidence=ev_list,
                        pressure=kv.get("pressure", ""),
                        affected=aff_list,
                        confidence=kv.get("confidence", "high"),
                        likely_level=kv.get("likely-level", "L1"),
                        blast_radius=kv.get("blast-radius", "local"),
                        product_intent_required=intent_req,
                        rank=rank_val,
                        status=kv.get("status", "deferred"),
                        reason=kv.get("reason", ""),
                        correctness_risk=kv.get("correctness-risk"),
                        operational_risk=kv.get("operational-risk"),
                        debt_interest=kv.get("debt-interest"),
                        change_propagation=kv.get("change-propagation"),
                        state_ambiguity=kv.get("state-ambiguity"),
                        scope_boundedness=kv.get("scope-boundedness"),
                        reversibility=kv.get("reversibility"),
                        structural_confidence=kv.get("structural-confidence"),
                        line_number=idx,
                    )
                )

    # 6. Parse Scope and Protected Contracts (C-n, H-n, A-n, TD-n)
    scope_body, scope_line = _section(text, "Scope and Protected Contracts")
    if scope_body:
        for idx, line in enumerate(scope_body.splitlines(), start=scope_line or 1):
            line_str = line.strip()
            if line_str.startswith("- C-"):
                c_id, kv = _parse_record_kv(line_str)
                assessment.contracts.append(
                    ContractRecord(
                        id=c_id,
                        status=kv.get("status", "preserved"),
                        contract=kv.get("contract", ""),
                        authorization=kv.get("authorization", "none"),
                        owner=kv.get("owner"),
                        resolution=kv.get("resolution"),
                        blocking=kv.get("blocking", "false").lower() == "true",
                        line_number=idx,
                    )
                )
            elif line_str.startswith("- H-"):
                h_id, kv = _parse_record_kv(line_str)
                assessment.handoff = HandoffRecord(
                    id=h_id,
                    status=kv.get("status", "assessment-only"),
                    next=kv.get("next", ""),
                    line_number=idx,
                )
            elif line_str.startswith("- A-"):
                a_id, kv = _parse_record_kv(line_str)
                assessment.assumptions.append(
                    AssumptionRecord(
                        id=a_id,
                        status=kv.get("status", "unconfirmed"),
                        impact=kv.get("impact", ""),
                        verification=kv.get("verification", ""),
                        line_number=idx,
                    )
                )
            elif line_str.startswith("- TD-"):
                td_id, kv = _parse_record_kv(line_str)
                ev_list = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]
                assessment.tech_debts.append(
                    TechDebtRecord(
                        id=td_id,
                        type=kv.get("type", "structural"),
                        evidence=ev_list,
                        principal=kv.get("principal", ""),
                        interest=kv.get("interest", ""),
                        frequency=kv.get("frequency", "current"),
                        blast_radius=kv.get("blast-radius", ""),
                        disposition=kv.get("disposition", "repay"),
                        reason=kv.get("reason", ""),
                        repayment_boundary=kv.get("repayment-boundary", kv.get("boundary", "")),
                        recurrence_guard=kv.get("recurrence-guard", ""),
                        revisit_trigger=kv.get("revisit-trigger", kv.get("revisit", "")),
                        containment_boundary=kv.get("containment-boundary"),
                        line_number=idx,
                    )
                )

    # 7. Parse Design Pressures and Classification (P-n and D-n)
    dp_body, dp_line = _section(text, "Design Pressures and Classification")
    if dp_body:
        for idx, line in enumerate(dp_body.splitlines(), start=dp_line or 1):
            line_str = line.strip()
            if line_str.startswith("- P-"):
                p_id, kv = _parse_record_kv(line_str)
                ev_list = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]
                rank_val = int(kv.get("rank", "1")) if kv.get("rank", "").isdigit() else 1
                assessment.pressures.append(
                    PressureRecord(
                        id=p_id,
                        rank=rank_val,
                        evidence=ev_list,
                        pressure=kv.get("pressure", ""),
                        line_number=idx,
                    )
                )
            elif line_str.startswith("- D-"):
                d_id, kv = _parse_record_kv(line_str)
                bec_list = [b.strip() for b in kv.get("because", "").split(",") if b.strip()]
                assessment.decision = DecisionRecord(
                    id=d_id,
                    level=kv.get("level", "L0"),
                    selected=kv.get("selected", ""),
                    because=bec_list,
                    rejected=kv.get("rejected", ""),
                    line_number=idx,
                )

    # 8. Parse Alternatives and Pattern Decisions (O-n and G-n)
    alt_body, alt_line = _section(text, "Alternatives and Pattern Decisions")
    if alt_body:
        lines = alt_body.splitlines()
        idx = 0
        while idx < len(lines):
            line_str = lines[idx].strip()
            curr_line_num = (alt_line or 1) + idx
            if line_str.startswith("- O-"):
                o_id, kv = _parse_record_kv(line_str)
                assessment.alternatives.append(
                    AlternativeRecord(
                        id=o_id,
                        level=kv.get("level", "L0"),
                        selected=kv.get("selected", "no").lower() in {"yes", "true"},
                        concepts=kv.get("concepts", ""),
                        arg_for=kv.get("argument-for", ""),
                        arg_against=kv.get("argument-against", ""),
                        revisit=kv.get("revisit", ""),
                        line_number=curr_line_num,
                    )
                )
            elif line_str.startswith("### G-") or line_str.startswith("- G-"):
                g_id = ""
                pattern_name = ""
                result_val = "admit"
                scope_val = "introduced"
                evidence_val: list[str] = []

                if line_str.startswith("### G-"):
                    g_header = line_str.lstrip("#").strip()
                    g_parts = g_header.split(":", 1)
                    g_id = g_parts[0].strip()
                    if len(g_parts) > 1:
                        p_res = g_parts[1].split("—", 1) if "—" in g_parts[1] else g_parts[1].split("-", 1)
                        pattern_name = p_res[0].strip()
                        if len(p_res) > 1:
                            result_val = p_res[1].strip()
                else:
                    g_id, kv = _parse_record_kv(line_str)
                    pattern_name = kv.get("pattern", "")
                    scope_val = kv.get("scope", "introduced")
                    result_val = kv.get("result", "admit")
                    evidence_val = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]

                questions_dict: dict[int, QuestionAnswer] = {}
                removed_dest = None
                revisit_trig = None

                sub_idx = idx + 1
                while sub_idx < len(lines):
                    sub_line = lines[sub_idx].strip()
                    if sub_line.startswith("### G-") or sub_line.startswith("- G-") or sub_line.startswith("- O-") or sub_line.startswith("## "):
                        break
                    if sub_line.startswith("- Scope:"):
                        _, kv = _parse_record_kv(sub_line)
                        scope_val = kv.get("Scope", scope_val)
                        result_val = kv.get("Result", result_val)
                        if "Evidence" in kv:
                            evidence_val = [e.strip() for e in kv["Evidence"].split(",") if e.strip()]
                        removed_dest = kv.get("removed-destination")
                        revisit_trig = kv.get("revisit-trigger")
                    elif sub_line.startswith("| Q") or (sub_line.startswith("|") and "Gate" not in sub_line and "---" not in sub_line):
                        cols = [c.strip() for c in sub_line.split("|")[1:-1]]
                        if len(cols) >= 3 and cols[0].startswith("Q"):
                            q_num_str = cols[0].lstrip("Q")
                            if q_num_str.isdigit():
                                q_num = int(q_num_str)
                                q_ans = cols[1].lower()
                                q_ev = [e.strip() for e in cols[2].split(",") if e.strip()]
                                q_cons = cols[3] if len(cols) > 3 else ""
                                questions_dict[q_num] = QuestionAnswer(
                                    number=q_num,
                                    answer=q_ans,
                                    evidence=q_ev,
                                    consequence=q_cons,
                                )
                    sub_idx += 1

                assessment.pattern_gates.append(
                    PatternGateRecord(
                        id=g_id,
                        pattern=pattern_name,
                        scope=scope_val,
                        result=result_val,
                        questions=questions_dict,
                        evidence=evidence_val,
                        removed_destination=removed_dest,
                        revisit_trigger=revisit_trig,
                        line_number=curr_line_num,
                    )
                )
            idx += 1

    # 9. Parse Verification and Residual Risk (V-n and R-n)
    v_body, v_line = _section(text, "Verification and Residual Risk")
    if v_body:
        for idx, line in enumerate(v_body.splitlines(), start=v_line or 1):
            line_str = line.strip()
            if line_str.startswith("- V-"):
                v_id, kv = _parse_record_kv(line_str)
                prov_list = [pr.strip() for pr in kv.get("proves", "").split(",") if pr.strip()]
                assessment.verifications.append(
                    VerificationRecord(
                        id=v_id,
                        proves=prov_list,
                        method=kv.get("method", ""),
                        expected=kv.get("expected", ""),
                        line_number=idx,
                    )
                )
            elif line_str.startswith("- R-"):
                r_id, kv = _parse_record_kv(line_str)
                assessment.residual_risks.append(
                    ResidualRiskRecord(
                        id=r_id,
                        severity=kv.get("severity", "low"),
                        scenario=kv.get("scenario", ""),
                        consequence=kv.get("consequence", ""),
                        owner=kv.get("owner", ""),
                        follow_up=kv.get("follow-up", ""),
                        line_number=idx,
                    )
                )

    # 10. Parse Migration and Rollback (M-n)
    m_body, m_line = _section(text, "Migration and Rollback")
    if m_body:
        for idx, line in enumerate(m_body.splitlines(), start=m_line or 1):
            line_str = line.strip()
            if line_str.startswith("- M-"):
                m_id, kv = _parse_record_kv(line_str)
                pres_list = [pr.strip() for pr in kv.get("preserved", "").split(",") if pr.strip()]
                proof_list = [pr.strip() for pr in kv.get("proof", "").split(",") if pr.strip()]
                assessment.migrations.append(
                    MigrationRecord(
                        id=m_id,
                        prerequisite=kv.get("prerequisite", ""),
                        changed_boundary=kv.get("changed boundary", kv.get("changed-boundary", "")),
                        preserved=pres_list,
                        proof=proof_list,
                        rollback_trigger=kv.get("rollback trigger", kv.get("rollback-trigger", "")),
                        rollback_action=kv.get("rollback action", kv.get("rollback-action", "")),
                        cleanup=kv.get("cleanup", ""),
                        line_number=idx,
                    )
                )

    return assessment, diagnostics


def validate(
    assessment_or_text: Assessment | str,
    declared_level: str | None = None,
    repo_root: Path = Path("."),
    *,
    require_finalized: bool = False,
) -> list[Diagnostic]:
    if isinstance(assessment_or_text, str):
        assessment, diagnostics = parse_assessment(assessment_or_text)
        text = assessment_or_text
    else:
        assessment = assessment_or_text
        diagnostics = list(assessment.diagnostics)
        text = assessment.raw_text

    effective_level = declared_level or assessment.level

    if require_finalized:
        diagnostics.extend(validate_receipt(text, required=True, expected_level_or_mode=effective_level))

    if effective_level != assessment.level:
        diagnostics.append(Diagnostic("level.declared.mismatch", f"Declared level {effective_level} != assessment level {assessment.level}"))

    mode = assessment.mode
    is_discovery_only = (mode == "discovery-only" or effective_level == "discovery-only")

    valid_record_ids = (
        {f.id for f in assessment.facts}
        | {e.id for e in assessment.external_facts}
        | {c.id for c in assessment.contracts}
        | {p.id for p in assessment.pressures}
        | ({assessment.decision.id} if assessment.decision else set())
        | {o.id for o in assessment.alternatives}
        | {g.id for g in assessment.pattern_gates}
        | {td.id for td in assessment.tech_debts}
        | {t.id for t in assessment.discovery_candidates}
        | {m.id for m in assessment.migrations}
        | {v.id for v in assessment.verifications}
    )

    # Mode 1: Targeted Mode Rules
    if mode == "targeted":
        if not assessment.facts and not assessment.external_facts:
            diagnostics.append(Diagnostic("fact.format", "Targeted assessment requires at least one F-n or E-n fact."))
        if not assessment.contracts:
            diagnostics.append(Diagnostic("contract.record.missing", "Targeted assessment requires at least one C-n contract."))
        if not assessment.pressures:
            diagnostics.append(Diagnostic("pressure.record.missing", "Targeted assessment requires at least one P-n pressure."))
        if not assessment.decision:
            diagnostics.append(Diagnostic("decision.record.missing", "Targeted assessment requires exactly one D-n decision record."))
        if not assessment.verifications:
            diagnostics.append(Diagnostic("verification.record.missing", "Targeted assessment requires at least one V-n verification record."))
        if not assessment.handoff:
            diagnostics.append(Diagnostic("handoff.record.missing", "Targeted assessment requires exactly one H-n handoff record."))
        if assessment.discovery_candidates:
            for tc in assessment.discovery_candidates:
                if tc.status == "selected":
                    diagnostics.append(Diagnostic("discovery.targeted.selected_prohibited", "Targeted mode prohibits selected T-n candidates.", tc.line_number))

    # Mode 2: Autonomous Discovery Mode Rules
    elif mode == "autonomous-discovery":
        if not (1 <= len(assessment.discovery_candidates) <= 5):
            diagnostics.append(Diagnostic("discovery.candidates.count_invalid", f"Autonomous discovery mode requires 1 to 5 T-n candidates, found {len(assessment.discovery_candidates)}."))
        
        ranks = [tc.rank for tc in assessment.discovery_candidates]
        if len(ranks) != len(set(ranks)):
            diagnostics.append(Diagnostic("discovery.candidates.duplicate_ranks", "T-n candidates must have unique ranks."))

        selected_candidates = [tc for tc in assessment.discovery_candidates if tc.status == "selected"]
        if len(selected_candidates) != 1:
            diagnostics.append(Diagnostic("discovery.autonomous.selected_count_invalid", f"Autonomous discovery mode requires exactly one selected candidate, found {len(selected_candidates)}."))
        else:
            sel = selected_candidates[0]
            if sel.confidence not in {"high", "medium"}:
                diagnostics.append(Diagnostic("discovery.autonomous.low_confidence", f"Selected candidate {sel.id} must be high or medium confidence, got {sel.confidence}.", sel.line_number))
            if sel.product_intent_required:
                diagnostics.append(Diagnostic("discovery.autonomous.product_intent_required", f"Selected candidate {sel.id} requires product intent alignment; must trigger discovery-only mode.", sel.line_number))
            if not sel.evidence:
                diagnostics.append(Diagnostic("discovery.autonomous.evidence_missing", f"Selected candidate {sel.id} must cite valid evidence.", sel.line_number))
            if not sel.affected:
                diagnostics.append(Diagnostic("discovery.autonomous.affected_missing", f"Selected candidate {sel.id} must cite affected contracts.", sel.line_number))
            if sel.rank != 1:
                diagnostics.append(Diagnostic("discovery.autonomous.rank_invalid", f"Selected candidate {sel.id} must have rank 1.", sel.line_number))

            if assessment.decision_summary and assessment.decision_summary.target and assessment.decision_summary.target != sel.target:
                diagnostics.append(Diagnostic("summary.target.mismatch", f"Decision Summary target '{assessment.decision_summary.target}' != selected candidate target '{sel.target}'"))
            if assessment.decision and assessment.decision.selected and sel.target.casefold() not in assessment.decision.selected.casefold() and assessment.decision.selected.casefold() not in sel.target.casefold():
                diagnostics.append(Diagnostic("decision.target.mismatch", f"Decision selected '{assessment.decision.selected}' does not match candidate target '{sel.target}'", assessment.decision.line_number))

    # Mode 3: Discovery-Only Mode Rules
    elif is_discovery_only:
        if not (1 <= len(assessment.discovery_candidates) <= 5):
            diagnostics.append(Diagnostic("discovery.candidates.count_invalid", f"Discovery-only mode requires 1 to 5 T-n candidates, found {len(assessment.discovery_candidates)}."))
        selected_candidates = [tc for tc in assessment.discovery_candidates if tc.status == "selected"]
        if selected_candidates:
            diagnostics.append(Diagnostic("discovery.only.selected_prohibited", f"Discovery-only mode prohibits selected candidates, found {len(selected_candidates)}.", selected_candidates[0].line_number))
        for tc in assessment.discovery_candidates:
            if not tc.reason or tc.reason.strip() == "":
                diagnostics.append(Diagnostic("discovery.only.reason_missing", f"Candidate {tc.id} in discovery-only mode must state a refusal reason.", tc.line_number))
        
        if assessment.decision:
            diagnostics.append(Diagnostic("discovery.only.decision_prohibited", "Discovery-only mode prohibits D-n decision records."))
        for alt in assessment.alternatives:
            if alt.selected:
                diagnostics.append(Diagnostic("discovery.only.selected_alt_prohibited", "Discovery-only mode prohibits selected O-n alternatives.", alt.line_number))
        if assessment.pattern_gates:
            diagnostics.append(Diagnostic("discovery.only.pattern_prohibited", "Discovery-only mode prohibits G-n pattern gate records."))
        if assessment.migrations:
            diagnostics.append(Diagnostic("discovery.only.migration_prohibited", "Discovery-only mode prohibits M-n migration records."))

        if assessment.handoff:
            if assessment.handoff.next != "codebase-issue-auditor":
                diagnostics.append(Diagnostic("discovery.only.handoff_invalid", f"Discovery-only mode handoff must be codebase-issue-auditor, got '{assessment.handoff.next}'", assessment.handoff.line_number))

    # Decision Summary Consistency Validation
    if assessment.decision_summary:
        ds = assessment.decision_summary
        if ds.mode and ds.mode != mode:
            diagnostics.append(Diagnostic("summary.mode.mismatch", f"Decision Summary mode '{ds.mode}' != assessment mode '{mode}'"))
        if ds.level and ds.level != effective_level:
            diagnostics.append(Diagnostic("summary.level.mismatch", f"Decision Summary level '{ds.level}' != declared level '{effective_level}'"))
        if ds.next_owner and assessment.handoff and ds.next_owner != assessment.handoff.next:
            diagnostics.append(Diagnostic("summary.next_owner.mismatch", f"Decision Summary next_owner '{ds.next_owner}' != Handoff next '{assessment.handoff.next}'"))

    # General Fact & Evidence Validation
    valid_fact_ids = {f.id for f in assessment.facts} | {e.id for e in assessment.external_facts}
    root = repo_root.resolve()

    for f in assessment.facts:
        if f.source not in VALID_SOURCES:
            diagnostics.append(Diagnostic("fact.source.invalid", f"Fact {f.id} has invalid source '{f.source}'", f.line_number))
        if f.strength not in VALID_STRENGTHS:
            diagnostics.append(Diagnostic("fact.strength.invalid", f"Fact {f.id} has invalid strength '{f.strength}'", f.line_number))
        if f.freshness not in VALID_FRESHNESS:
            diagnostics.append(Diagnostic("fact.freshness.invalid", f"Fact {f.id} has invalid freshness '{f.freshness}'", f.line_number))

        if f.path.startswith("git-history:"):
            if not GIT_HISTORY_LOCATOR_RE.match(f.path):
                diagnostics.append(Diagnostic("fact.git_history.malformed", f"Fact {f.id} has malformed git-history locator '{f.path}'", f.line_number))
        elif f.source not in {"repository-history", "fixture"}:
            fact_path = root / f.path.split(":")[0]
            if not fact_path.is_file():
                diagnostics.append(Diagnostic("fact.path.missing", f"Fact {f.id} path '{f.path}' does not exist on disk", f.line_number))

    for ef in assessment.external_facts:
        if ef.freshness not in VALID_FRESHNESS:
            diagnostics.append(Diagnostic("fact.freshness.invalid", f"External fact {ef.id} has invalid freshness '{ef.freshness}'", ef.line_number))

    # L2/L3 Evidence Checks
    if effective_level in {"L2", "L3"} and not is_discovery_only:
        valid_facts = [f for f in assessment.facts if f.source in VALID_SOURCES]
        sources_used = {f.source for f in valid_facts}

        if effective_level == "L3":
            if len(sources_used) < 3:
                diagnostics.append(Diagnostic("evidence.l3.categories_insufficient", f"L3 assessment requires at least 3 distinct evidence categories, found {len(sources_used)} ({sources_used})"))

            # Require representation across pillars
            code_pillar = {"code", "test", "runtime"} & sources_used
            state_pillar = {"schema", "configuration", "ownership", "production"} & sources_used
            ops_pillar = {"deployment", "production", "ownership", "repository-history"} & sources_used
            if not code_pillar or not state_pillar or not ops_pillar:
                diagnostics.append(Diagnostic("evidence.l3.pillar_missing", f"L3 evidence must span code ({code_pillar}), state/contracts ({state_pillar}), and operations/history ({ops_pillar})"))

        strengths_used = {f.strength for f in valid_facts}
        if strengths_used == {"inferred"}:
            diagnostics.append(Diagnostic("evidence.l2_l3.inferred_only", "L2/L3 design cannot be approved solely by inferred evidence"))

        freshness_used = {f.freshness for f in valid_facts}
        if freshness_used.issubset({"potentially-stale", "historical"}):
            diagnostics.append(Diagnostic("evidence.stale_only", "Stale evidence alone cannot override or establish current local behavior"))

    # Pressure Validation
    for p in assessment.pressures:
        if not p.evidence:
            diagnostics.append(Diagnostic("pressure.evidence.missing", f"Pressure {p.id} must cite at least one F-n or E-n fact", p.line_number))
        else:
            for ev_id in p.evidence:
                if ev_id not in valid_fact_ids:
                    diagnostics.append(Diagnostic("pressure.evidence.invalid", f"Pressure {p.id} cites unknown evidence '{ev_id}'", p.line_number))

    p_ranks = [p.rank for p in assessment.pressures]
    if len(p_ranks) != len(set(p_ranks)):
        diagnostics.append(Diagnostic("pressure.rank.duplicate", "P-n pressures must have unique ranks."))

    # Contract Validation
    for c in assessment.contracts:
        if c.status == "authorized-change" and (not c.authorization or c.authorization == "none"):
            diagnostics.append(Diagnostic("contract.authorization.missing", f"Contract {c.id} with authorized-change must name explicit authorization", c.line_number))
        elif c.status == "at-risk":
            if not c.owner or not c.resolution:
                diagnostics.append(Diagnostic("contract.at_risk.incomplete", f"Contract {c.id} at-risk must specify owner and resolution", c.line_number))
            if c.blocking:
                diagnostics.append(Diagnostic("contract.at_risk.unresolved", f"Contract {c.id} remains unresolved blocking contract", c.line_number))

    # Decision & Alternatives Validation
    if assessment.decision and not is_discovery_only:
        d = assessment.decision
        if d.level != effective_level:
            diagnostics.append(Diagnostic("decision.level.mismatch", f"Decision level {d.level} != declared level {effective_level}", d.line_number))
        if not d.because:
            diagnostics.append(Diagnostic("decision.because.missing", f"Decision {d.id} must cite facts/pressures in because", d.line_number))
        if not d.rejected:
            diagnostics.append(Diagnostic("decision.rejected.missing", f"Decision {d.id} must explain why lower level was rejected", d.line_number))

        selected_alts = [a for a in assessment.alternatives if a.selected]
        if len(selected_alts) != 1:
            diagnostics.append(Diagnostic("alternatives.selected.count_invalid", f"Exactly one selected O-n alternative required, found {len(selected_alts)}."))
        else:
            sel_alt = selected_alts[0]
            if sel_alt.level != d.level:
                diagnostics.append(Diagnostic("alternatives.selected.level_mismatch", f"Selected alternative O-n level {sel_alt.level} != D-n level {d.level}", sel_alt.line_number))

        if effective_level in {"L2", "L3"}:
            has_lower = any(a.level in {"L0", "L1"} for a in assessment.alternatives)
            if not has_lower:
                diagnostics.append(Diagnostic("alternatives.l2_l3.lower_level_missing", f"{effective_level} assessment must include L0 or L1 alternative"))

    # Pattern Gate Validation
    for g in assessment.pattern_gates:
        if g.questions and g.result in {"admit", "admit-narrowed"}:
            for hard_q in HARD_PATTERN_QUESTIONS:
                if hard_q in g.questions:
                    qa = g.questions[hard_q]
                    if qa.answer != "yes":
                        diagnostics.append(Diagnostic("pattern.hard_gate.failed", f"Pattern gate {g.id} result '{g.result}' requires Q{hard_q}=yes, got '{qa.answer}'", g.line_number))
                else:
                    diagnostics.append(Diagnostic("pattern.hard_gate.missing", f"Pattern gate {g.id} requires question Q{hard_q}", g.line_number))
        if g.scope == "removed" or g.result == "remove":
            if not g.removed_destination or g.removed_destination.strip() == "":
                diagnostics.append(Diagnostic("pattern.removal.destination_missing", f"Pattern removal {g.id} must state removed-destination", g.line_number))
        if g.result == "defer" and not g.revisit_trigger:
            diagnostics.append(Diagnostic("pattern.defer.revisit_missing", f"Pattern deferral {g.id} must specify revisit-trigger", g.line_number))

    # Technical Debt Validation
    for td in assessment.tech_debts:
        if td.type not in VALID_DEBT_TYPES:
            diagnostics.append(Diagnostic("tech_debt.type.invalid", f"Technical debt {td.id} invalid type '{td.type}'", td.line_number))
        if td.disposition not in VALID_DEBT_DISPOSITIONS:
            diagnostics.append(Diagnostic("tech_debt.disposition.invalid", f"Technical debt {td.id} invalid disposition '{td.disposition}'", td.line_number))
        if td.disposition in {"repay", "retire"} and (not td.recurrence_guard or td.recurrence_guard.lower() in {"none", "n/a"}):
            diagnostics.append(Diagnostic("tech_debt.recurrence_guard.missing", f"Technical debt {td.id} disposition '{td.disposition}' requires recurrence-guard", td.line_number))
        if td.disposition in {"accept", "monitor", "contain"} and (not td.revisit_trigger or td.revisit_trigger.lower() in {"none", "n/a"}):
            diagnostics.append(Diagnostic("tech_debt.revisit_trigger.missing", f"Technical debt {td.id} disposition '{td.disposition}' requires revisit-trigger", td.line_number))
        if td.disposition == "contain" and not td.containment_boundary:
            diagnostics.append(Diagnostic("tech_debt.containment_boundary.missing", f"Technical debt {td.id} disposition contain requires containment-boundary", td.line_number))

    # Verification Validation
    for v in assessment.verifications:
        if not v.proves:
            diagnostics.append(Diagnostic("verification.proves.missing", f"Verification {v.id} must state proves", v.line_number))
        else:
            for p_item in v.proves:
                if p_item.startswith("V-") or p_item.startswith("H-") or p_item not in valid_record_ids:
                    diagnostics.append(Diagnostic("verification.proves.invalid", f"Verification {v.id} cannot prove self/handoff or unknown record '{p_item}'", v.line_number))
        if not v.method or not v.expected:
            diagnostics.append(Diagnostic("verification.method_expected.missing", f"Verification {v.id} requires concrete method and expected result", v.line_number))

    # Migration Validation
    for m in assessment.migrations:
        if not m.rollback_trigger or not m.rollback_action:
            diagnostics.append(Diagnostic("migration.rollback.missing", f"Migration {m.id} requires rollback trigger and action", m.line_number))

    # Handoff Validation
    if assessment.handoff:
        h = assessment.handoff
        if h.next not in VALID_HANDOFFS:
            diagnostics.append(Diagnostic("handoff.next.invalid", f"Handoff next '{h.next}' must be one of {sorted(VALID_HANDOFFS)}", h.line_number))
        if assessment.decision_summary and assessment.decision_summary.next_owner:
            if assessment.decision_summary.next_owner != h.next:
                diagnostics.append(Diagnostic("summary.next_owner.mismatch", f"Decision Summary next_owner '{assessment.decision_summary.next_owner}' != Handoff next '{h.next}'", h.line_number))
        if h.next == "implement-with-senior-dev":
            # Must explicitly evidence an approved plan
            plan_ev = [f for f in assessment.facts if "plan" in f.observation.casefold() or "plan" in f.path.casefold()]
            if not plan_ev:
                diagnostics.append(Diagnostic("handoff.implement.unplanned", "Handoff to implement-with-senior-dev requires an approved, decision-complete plan in evidence", h.line_number))

    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a design codebase assessment artifact.")
    parser.add_argument("assessment_file", help="Path to assessment markdown file.")
    parser.add_argument("--level", required=False, help="Declared assessment level (L0, L1, L2, L3, discovery-only).")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--require-finalized", action="store_true", help="Require valid SHA-256 finalization receipt.")
    parser.add_argument("--json", action="store_true", help="Emit diagnostics in JSON format.")
    args = parser.parse_args()

    file_path = Path(args.assessment_file)
    if not file_path.is_file():
        err = [Diagnostic("file.missing", f"File not found: {file_path}")]
        if args.json:
            print(json.dumps([e.to_dict() for e in err]))
        else:
            print(f"Error: {file_path} not found.", file=sys.stderr)
        return 1

    text = file_path.read_text(encoding="utf-8")
    diagnostics = validate(text, args.level, Path(args.repo_root), require_finalized=args.require_finalized)

    errors = [d for d in diagnostics if not d.is_warning]
    if args.json:
        print(json.dumps([d.to_dict() for d in diagnostics], indent=2))
    else:
        for d in diagnostics:
            print(str(d), file=sys.stderr if not d.is_warning else sys.stdout)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
