#!/usr/bin/env python3
"""Check a design-codebase-with-senior-dev assessment artifact against Contract v2."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import (  # noqa: E402
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
    compute_candidate_score,
    load_contract,
    section_names,
    validate_receipt,
)

EXACT_PLACEHOLDERS = {
    "replace",
    "replace with",
    "explicitly defined",
    "not applicable",
    "not-applicable",
    "none",
    "tbd",
    "todo",
    "n/a",
    "na",
    "fill this in",
    "none because local",
    "not-applicable: verified",
    "tbd later",
    "replace with concrete reason",
}

SUPERFICIAL_KEYWORDS = [
    "file is old",
    "file age",
    "old file",
    "too many lines",
    "lines long",
    "file length",
    "todo in code",
    "todo comment",
    "style dislike",
    "dislike style",
    "legacy code",
    "subjective complexity",
]


def _normalize_text(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[\*\_`]", "", s)
    s = re.sub(r"[\s\:\.\,\;\-\_\(\)\[\]]+", " ", s).strip()
    return s


def _is_placeholder(text: str) -> bool:
    if not text or not text.strip():
        return True
    stripped = text.strip()
    if re.match(r"^replace-l[0-3]-design$", stripped, re.IGNORECASE) or re.match(r"^replace-design$", stripped, re.IGNORECASE) or re.match(r"^replace pattern$", stripped, re.IGNORECASE):
        return False
    norm = _normalize_text(text)
    if norm in EXACT_PLACEHOLDERS:
        return True
    if norm.startswith("replace ") or norm.startswith("todo ") or norm.startswith("tbd "):
        return True
    return False


def _is_superficial_debt_claim(principal: str, reason: str) -> bool:
    combined = f"{principal} {reason}".lower()
    norm = _normalize_text(combined)
    for kw in SUPERFICIAL_KEYWORDS:
        if kw in combined or kw in norm:
            cost_words = [
                "propagation",
                "volatility",
                "coupling",
                "duplication",
                "state",
                "concurrency",
                "testability",
                "failure",
                "leak",
                "overhead",
            ]
            if not any(w in norm for w in cost_words):
                return True
    return False


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

    all_record_ids: list[tuple[str, int]] = []
    all_handoffs: list[HandoffRecord] = []
    all_decisions: list[DecisionRecord] = []

    # 1. Parse Title
    title_match = re.search(r"^# (?P<title>.+)$", text, re.MULTILINE)
    if title_match:
        assessment.title = title_match.group("title").strip()

    # 2. Parse Marker
    marker_match = re.search(
        r"<!-- design-assessment-contract: (?P<version>\d+); (?:level: (?P<level>L[0-3])(?:; mode: (?P<mode_in_level>targeted|autonomous-discovery))?|mode: (?P<mode>discovery-only)) -->",
        text,
    )
    if not marker_match:
        diagnostics.append(
            Diagnostic(
                "contract.marker.missing",
                "Missing contract marker <!-- design-assessment-contract: 2; level: L0..L3 --> or mode: discovery-only",
            )
        )
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
            assessment.mode = marker_match.group("mode_in_level") or "targeted"

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
            elif line_str.startswith("- Selected design-id:"):
                ds.selected_design_id = line_str.split(":", 1)[1].strip()
        assessment.decision_summary = ds
    elif assessment.mode != "discovery-only":
        diagnostics.append(Diagnostic("summary.section.missing", "Section ## Decision Summary is required", summary_line))

    # 4. Line by line record scanning
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_number = idx + 1
        line_str = line.strip()

        # F-n fact parsing
        if line_str.startswith("- F-"):
            f_match = re.match(
                r"^-\s*(?P<id>F-\d+):\s*`(?P<path>git-history:[^\s:`]+:[^\s:`]+:\d+|git-history:[^\s:`]+:[^\s:`]+|[^`:]+?)(?::(?P<line>\d+))?`\s*\|\s*anchor:\s*`(?P<anchor>[^`]*)`\s*\|\s*observation:\s*(?P<obs>.*?)(?:\s*\|\s*source:\s*(?P<source>[^|]+))?(?:\s*\|\s*strength:\s*(?P<strength>[^|]+))?(?:\s*\|\s*freshness:\s*(?P<freshness>[^|]+))?$",
                line_str,
            )
            if f_match:
                rec_id = f_match.group("id")
                all_record_ids.append((rec_id, line_number))
                path_str = f_match.group("path")
                line_val = 1
                if f_match.group("line"):
                    line_val = int(f_match.group("line"))
                elif path_str.startswith("git-history:") and path_str.count(":") >= 3:
                    line_val = int(path_str.rsplit(":", 1)[1])

                assessment.facts.append(
                    FactRecord(
                        id=rec_id,
                        path=path_str,
                        line=line_val,
                        anchor=f_match.group("anchor"),
                        observation=f_match.group("obs").strip(),
                        source=(f_match.group("source") or "code").strip(),
                        strength=(f_match.group("strength") or "direct").strip(),
                        freshness=(f_match.group("freshness") or "current").strip().rstrip("."),
                        line_number=line_number,
                    )
                )

        # E-n external fact parsing
        elif line_str.startswith("- E-"):
            e_match = re.match(
                r"^-\s*(?P<id>E-\d+):\s*source:\s*`(?P<source>[^`]*)`\s*\|\s*version:\s*`(?P<ver>[^`]*)`\s*\|\s*claim:\s*(?P<claim>.*?)(?:\s*\|\s*freshness:\s*(?P<freshness>[^|]+))?(?:\s*\|\s*relationship:\s*(?P<rel>[^|]+))?(?:\s*\|\s*authoritative:\s*(?P<auth>[^|]+))?$",
                line_str,
            )
            if e_match:
                rec_id = e_match.group("id")
                all_record_ids.append((rec_id, line_number))
                assessment.external_facts.append(
                    ExternalFactRecord(
                        id=rec_id,
                        source_id=e_match.group("source"),
                        version=e_match.group("ver"),
                        claim=e_match.group("claim").strip(),
                        freshness=(e_match.group("freshness") or "current").strip(),
                        relationship=(e_match.group("rel") or "supports").strip(),
                        authoritative=(e_match.group("auth") or "true").strip().lower() == "true",
                        line_number=line_number,
                    )
                )

        # T-n candidate parsing
        elif line_str.startswith("- T-"):
            t_id, kv = _parse_record_kv(line_str)
            if t_id:
                all_record_ids.append((t_id, line_number))
                ev_list = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]
                aff_list = [a.strip() for a in kv.get("affected", "").split(",") if a.strip()]

                rank_str = kv.get("rank")
                if rank_str is None or not rank_str.isdigit():
                    diagnostics.append(
                        Diagnostic("discovery.candidate.rank_malformed", f"Candidate {t_id} missing or non-integer rank '{rank_str}'", line_number)
                    )
                    rank_val = -1
                else:
                    rank_val = int(rank_str)

                intent_raw = kv.get("product-intent-required", "false").lower()
                if intent_raw not in {"true", "false"}:
                    diagnostics.append(
                        Diagnostic("discovery.candidate.boolean_invalid", f"Candidate {t_id} product-intent-required must be true or false, got '{intent_raw}'", line_number)
                    )
                intent_req = (intent_raw == "true")

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
                        line_number=line_number,
                    )
                )

        # C-n contract parsing
        elif line_str.startswith("- C-"):
            c_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((c_id, line_number))
            assessment.contracts.append(
                ContractRecord(
                    id=c_id,
                    status=kv.get("status", "preserved"),
                    contract=kv.get("contract", ""),
                    authorization=kv.get("authorization", "none"),
                    owner=kv.get("owner"),
                    resolution=kv.get("resolution"),
                    blocking=kv.get("blocking", "false").lower() == "true",
                    line_number=line_number,
                )
            )

        # H-n handoff parsing
        elif line_str.startswith("- H-"):
            h_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((h_id, line_number))
            rec_h = HandoffRecord(
                id=h_id,
                status=kv.get("status", "assessment-only"),
                next=kv.get("next", ""),
                line_number=line_number,
            )
            all_handoffs.append(rec_h)
            assessment.handoff = rec_h

        # A-n assumption parsing
        elif line_str.startswith("- A-"):
            a_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((a_id, line_number))
            assessment.assumptions.append(
                AssumptionRecord(
                    id=a_id,
                    status=kv.get("status", "unconfirmed"),
                    impact=kv.get("impact", ""),
                    verification=kv.get("verification", ""),
                    line_number=line_number,
                )
            )

        # TD-n tech debt parsing
        elif line_str.startswith("- TD-"):
            td_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((td_id, line_number))
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
                    line_number=line_number,
                )
            )

        # P-n pressure parsing
        elif line_str.startswith("- P-"):
            p_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((p_id, line_number))
            ev_list = [e.strip() for e in kv.get("evidence", "").split(",") if e.strip()]
            rank_val = int(kv.get("rank", "1")) if kv.get("rank", "").isdigit() else 1
            assessment.pressures.append(
                PressureRecord(
                    id=p_id,
                    rank=rank_val,
                    evidence=ev_list,
                    pressure=kv.get("pressure", ""),
                    line_number=line_number,
                )
            )

        # D-n decision parsing
        elif line_str.startswith("- D-"):
            d_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((d_id, line_number))
            bec_list = [b.strip() for b in kv.get("because", "").split(",") if b.strip()]
            rec_d = DecisionRecord(
                id=d_id,
                level=kv.get("level", "L0"),
                selected=kv.get("selected", ""),
                because=bec_list,
                rejected=kv.get("rejected", ""),
                design_id=kv.get("design-id", kv.get("design_id", "")),
                line_number=line_number,
            )
            all_decisions.append(rec_d)
            assessment.decision = rec_d

        # O-n alternative parsing
        elif line_str.startswith("- O-"):
            o_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((o_id, line_number))
            assessment.alternatives.append(
                AlternativeRecord(
                    id=o_id,
                    level=kv.get("level", "L0"),
                    selected=kv.get("selected", "no").lower() in {"yes", "true"},
                    concepts=kv.get("concepts", ""),
                    arg_for=kv.get("argument-for", ""),
                    arg_against=kv.get("argument-against", ""),
                    revisit=kv.get("revisit", ""),
                    design_id=kv.get("design-id", kv.get("design_id", "")),
                    line_number=line_number,
                )
            )

        # G-n pattern gate parsing
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

            all_record_ids.append((g_id, line_number))
            questions_dict: dict[int, QuestionAnswer] = {}
            seen_q_nums: set[int] = set()
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
                            if q_num in seen_q_nums:
                                diagnostics.append(Diagnostic("pattern.question.duplicate", f"Pattern gate {g_id} contains duplicate row for Q{q_num}", sub_idx + 1))
                            else:
                                seen_q_nums.add(q_num)
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
                    line_number=line_number,
                )
            )
            idx = sub_idx - 1

        # V-n verification parsing
        elif line_str.startswith("- V-"):
            v_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((v_id, line_number))
            prov_list = [pr.strip() for pr in kv.get("proves", "").split(",") if pr.strip()]
            assessment.verifications.append(
                VerificationRecord(
                    id=v_id,
                    proves=prov_list,
                    method=kv.get("method", ""),
                    expected=kv.get("expected", ""),
                    line_number=line_number,
                )
            )

        # R-n residual risk parsing
        elif line_str.startswith("- R-"):
            r_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((r_id, line_number))
            assessment.residual_risks.append(
                ResidualRiskRecord(
                    id=r_id,
                    severity=kv.get("severity", "low"),
                    scenario=kv.get("scenario", ""),
                    consequence=kv.get("consequence", ""),
                    owner=kv.get("owner", ""),
                    follow_up=kv.get("follow-up", ""),
                    line_number=line_number,
                )
            )

        # M-n migration parsing
        elif line_str.startswith("- M-"):
            m_id, kv = _parse_record_kv(line_str)
            all_record_ids.append((m_id, line_number))
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
                    line_number=line_number,
                )
            )

        idx += 1

    # Duplicate Record ID Detection
    seen_ids: set[str] = set()
    for rec_id, line_num in all_record_ids:
        if rec_id in seen_ids:
            diagnostics.append(Diagnostic("record.id.duplicate", f"Duplicate record ID '{rec_id}' found", line_num))
        else:
            seen_ids.add(rec_id)

    if len(all_handoffs) > 1:
        diagnostics.append(Diagnostic("handoff.count.invalid", f"Assessment contains {len(all_handoffs)} H-n handoff records; exactly one required.", all_handoffs[1].line_number))

    if len(all_decisions) > 1:
        diagnostics.append(Diagnostic("decision.count.invalid", f"Assessment contains {len(all_decisions)} D-n decision records; exactly one allowed.", all_decisions[1].line_number))

    return assessment, diagnostics


def validate(
    assessment_or_text: Assessment | str,
    declared_level: str | None = None,
    repo_root: Path = Path("."),
    *,
    require_finalized: bool = False,
    allow_placeholders: bool = False,
) -> list[Diagnostic]:
    contract = load_contract()

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

    expected_mode = assessment.mode
    mode = expected_mode
    is_discovery_only = (mode == "discovery-only" or effective_level == "discovery-only")

    valid_fact_ids = {f.id for f in assessment.facts} | {e.id for e in assessment.external_facts}
    valid_contract_ids = {c.id for c in assessment.contracts}
    valid_pressure_ids = {p.id for p in assessment.pressures}
    valid_risk_ids = {r.id for r in assessment.residual_risks}
    valid_debt_ids = {td.id for td in assessment.tech_debts}

    valid_record_ids = (
        valid_fact_ids
        | valid_contract_ids
        | valid_pressure_ids
        | valid_risk_ids
        | valid_debt_ids
        | ({assessment.decision.id} if assessment.decision else set())
        | {o.id for o in assessment.alternatives}
        | {g.id for g in assessment.pattern_gates}
        | {t.id for t in assessment.discovery_candidates}
        | {m.id for m in assessment.migrations}
        | {v.id for v in assessment.verifications}
    )

    # 1. Section Presence, Order, and Body Validation
    expected_secs = section_names(effective_level, mode)
    found_headers = [(m.group(1).strip(), text[: m.start()].count("\n") + 1) for m in re.finditer(r"^## ([^\n]+)", text, re.MULTILINE)]
    found_sec_names = [h[0] for h in found_headers]

    for sec in expected_secs:
        if sec not in found_sec_names:
            diagnostics.append(Diagnostic("section.required.missing", f"Section ## {sec} is required for level {effective_level}"))
        else:
            body, line_num = _section(text, sec)
            if not body or not body.strip() or re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip() == "":
                diagnostics.append(Diagnostic("section.body.empty", f"Section ## {sec} body cannot be empty", line_num))

    filtered_found = [s for s in found_sec_names if s in expected_secs]
    expected_order_filtered = [s for s in expected_secs if s in filtered_found]
    if filtered_found != expected_order_filtered:
        diagnostics.append(Diagnostic("section.order.invalid", f"Sections are out of order for level {effective_level}. Expected {expected_secs}, got {filtered_found}"))

    # 2. Mode-Specific Rules & Autonomous Ranking
    cand_enums = contract.get("candidate_enums", {})
    ranking_weights = contract.get("candidate_ranking_weights", {})
    tie_threshold = float(contract.get("material_tie_threshold", 2.0))

    selected_candidates = [tc for tc in assessment.discovery_candidates if tc.status == "selected"]

    if mode == "targeted":
        if not assessment.facts and not assessment.external_facts:
            diagnostics.append(Diagnostic("fact.format", "Assessment requires at least one F-n or E-n fact."))
        if not assessment.contracts:
            diagnostics.append(Diagnostic("contract.record.missing", "Assessment requires at least one C-n contract."))
        if not assessment.pressures:
            diagnostics.append(Diagnostic("pressure.record.missing", "Assessment requires at least one P-n pressure."))
        if not assessment.decision:
            diagnostics.append(Diagnostic("decision.record.missing", "Assessment requires exactly one D-n decision record."))
        if not assessment.verifications:
            diagnostics.append(Diagnostic("verification.record.missing", "Assessment requires at least one V-n verification record."))
        if not assessment.handoff:
            diagnostics.append(Diagnostic("handoff.record.missing", "Assessment requires exactly one H-n handoff record."))

        if assessment.discovery_candidates:
            for tc in assessment.discovery_candidates:
                if tc.status == "selected":
                    diagnostics.append(Diagnostic("discovery.targeted.selected_prohibited", "Targeted mode prohibits selected T-n candidates.", tc.line_number))

    elif mode == "autonomous-discovery":
        if not (1 <= len(assessment.discovery_candidates) <= 5):
            diagnostics.append(Diagnostic("discovery.candidates.count_invalid", f"Autonomous discovery mode requires 1 to 5 T-n candidates, found {len(assessment.discovery_candidates)}."))

        ranks_seen: list[int] = [tc.rank for tc in assessment.discovery_candidates]
        for tc in assessment.discovery_candidates:
            if tc.rank <= 0:
                diagnostics.append(Diagnostic("discovery.candidate.rank_invalid", f"Candidate {tc.id} has invalid rank {tc.rank}", tc.line_number))

            if tc.status not in cand_enums.get("status", ["selected", "rejected", "deferred"]):
                diagnostics.append(Diagnostic("discovery.candidate.status_invalid", f"Candidate {tc.id} has invalid status '{tc.status}'", tc.line_number))

            if tc.confidence not in cand_enums.get("confidence", ["low", "medium", "high"]):
                diagnostics.append(Diagnostic("discovery.candidate.confidence_invalid", f"Candidate {tc.id} has invalid confidence '{tc.confidence}'", tc.line_number))

            if tc.likely_level not in cand_enums.get("likely_level", ["L0", "L1", "L2", "L3"]):
                diagnostics.append(Diagnostic("discovery.candidate.likely_level_invalid", f"Candidate {tc.id} has invalid likely_level '{tc.likely_level}'", tc.line_number))

            for rfield in ranking_weights:
                val = getattr(tc, rfield, None)
                valid_vals = cand_enums.get(rfield, [])
                if not val or val.lower() not in valid_vals:
                    diagnostics.append(Diagnostic("discovery.candidate.ranking_enum_invalid", f"Candidate {tc.id} field '{rfield}' has invalid/missing enum value '{val}'", tc.line_number))

        if len(ranks_seen) != len(set(ranks_seen)):
            diagnostics.append(Diagnostic("discovery.candidate.rank_duplicate", "Target candidate ranks must be unique."))

        valid_ranks = sorted([r for r in ranks_seen if r > 0])
        if valid_ranks and valid_ranks != list(range(1, len(valid_ranks) + 1)):
            diagnostics.append(Diagnostic("discovery.candidate.rank_non_contiguous", f"Target candidate ranks must be contiguous integers starting at 1, got {valid_ranks}"))

        # Evaluate candidate score ranking
        cand_scores: list[tuple[float, TargetCandidateRecord]] = [
            (compute_candidate_score(tc), tc) for tc in assessment.discovery_candidates
        ]
        cand_scores.sort(key=lambda item: (-item[0], item[1].id))

        for expected_rank, (score, tc) in enumerate(cand_scores, start=1):
            if tc.rank > 0 and tc.rank != expected_rank:
                diagnostics.append(
                    Diagnostic(
                        "discovery.autonomous.rank_score_mismatch",
                        f"Candidate {tc.id} rank {tc.rank} does not match calculated score rank {expected_rank} (score {score})",
                        tc.line_number,
                    )
                )

        # Check material tie threshold
        top_tied = False
        if len(cand_scores) >= 2:
            s1, tc1 = cand_scores[0]
            s2, tc2 = cand_scores[1]
            if (s1 - s2) <= tie_threshold:
                top_tied = True

        if top_tied:
            line_target = selected_candidates[0].line_number if selected_candidates else assessment.discovery_candidates[0].line_number
            diagnostics.append(
                Diagnostic(
                    "discovery.autonomous.ranking_tied",
                    f"Top candidate score difference ({cand_scores[0][0] - cand_scores[1][0]:.2f}) <= threshold ({tie_threshold}); material tie forces refusal / discovery-only mode.",
                    line_target,
                )
            )
        else:
            if len(selected_candidates) != 1:
                diagnostics.append(Diagnostic("discovery.autonomous.selected_count_invalid", f"Autonomous discovery mode requires exactly one selected candidate, found {len(selected_candidates)}."))
            else:
                sel = selected_candidates[0]
                if sel.rank != 1:
                    diagnostics.append(Diagnostic("discovery.autonomous.rank_invalid", f"Selected candidate {sel.id} must have rank 1.", sel.line_number))
                if sel.confidence not in {"high", "medium"}:
                    diagnostics.append(Diagnostic("discovery.autonomous.low_confidence", f"Selected candidate {sel.id} must be high or medium confidence, got {sel.confidence}.", sel.line_number))
                if sel.product_intent_required:
                    diagnostics.append(Diagnostic("discovery.autonomous.product_intent_required", f"Selected candidate {sel.id} requires product intent alignment; must trigger discovery-only mode.", sel.line_number))
                if sel.scope_boundedness and sel.scope_boundedness.lower() == "low":
                    diagnostics.append(Diagnostic("discovery.autonomous.unbounded", f"Selected candidate {sel.id} cannot be low scope-boundedness.", sel.line_number))
                if sel.reversibility and sel.reversibility.lower() == "low":
                    diagnostics.append(Diagnostic("discovery.autonomous.low_reversibility", f"Selected candidate {sel.id} cannot be low reversibility.", sel.line_number))
                if sel.structural_confidence and sel.structural_confidence.lower() == "low":
                    diagnostics.append(Diagnostic("discovery.autonomous.low_confidence", f"Selected candidate {sel.id} cannot be low structural_confidence.", sel.line_number))
                if not sel.evidence:
                    diagnostics.append(Diagnostic("discovery.autonomous.evidence_missing", f"Selected candidate {sel.id} must cite valid evidence.", sel.line_number))
                if not sel.affected:
                    diagnostics.append(Diagnostic("discovery.autonomous.affected_missing", f"Selected candidate {sel.id} must cite affected contracts.", sel.line_number))

                if assessment.decision_summary and assessment.decision_summary.target and assessment.decision_summary.target != sel.target:
                    if not allow_placeholders:
                        diagnostics.append(Diagnostic("summary.target.mismatch", f"Decision Summary target '{assessment.decision_summary.target}' != selected candidate target '{sel.target}'"))

        # Candidate citation validation
        for tc in assessment.discovery_candidates:
            for ev_id in tc.evidence:
                if ev_id not in valid_fact_ids:
                    diagnostics.append(Diagnostic("discovery.candidate.evidence_invalid", f"Candidate {tc.id} cites unknown evidence '{ev_id}'", tc.line_number))
            for aff_id in tc.affected:
                if aff_id not in valid_contract_ids:
                    diagnostics.append(Diagnostic("discovery.candidate.affected_invalid", f"Candidate {tc.id} cites unknown affected contract '{aff_id}'", tc.line_number))
            if tc.pressure and tc.pressure.lower() not in {"none", "n/a", "not-applicable", "not applicable"} and tc.pressure not in valid_pressure_ids:
                diagnostics.append(Diagnostic("discovery.candidate.pressure_invalid", f"Candidate {tc.id} cites unknown pressure '{tc.pressure}'", tc.line_number))

        if len(selected_candidates) == 1 and not top_tied:
            if not assessment.facts and not assessment.external_facts:
                diagnostics.append(Diagnostic("fact.format", "Autonomous assessment requires at least one F-n or E-n fact."))
            if not assessment.contracts:
                diagnostics.append(Diagnostic("contract.record.missing", "Autonomous assessment requires at least one C-n contract."))
            if not assessment.pressures:
                diagnostics.append(Diagnostic("pressure.record.missing", "Autonomous assessment requires at least one P-n pressure."))
            if not assessment.decision:
                diagnostics.append(Diagnostic("decision.record.missing", "Autonomous assessment requires exactly one D-n decision record."))
            if not assessment.verifications:
                diagnostics.append(Diagnostic("verification.record.missing", "Autonomous assessment requires at least one V-n verification record."))
            if not assessment.handoff:
                diagnostics.append(Diagnostic("handoff.record.missing", "Autonomous assessment requires exactly one H-n handoff record."))

    elif is_discovery_only:
        if not assessment.facts and not assessment.external_facts:
            diagnostics.append(Diagnostic("discovery.only.facts_missing", "Discovery-only mode requires at least one F-n or E-n fact."))
        if not assessment.contracts:
            diagnostics.append(Diagnostic("discovery.only.contracts_missing", "Discovery-only mode requires at least one C-n contract."))
        if not (1 <= len(assessment.discovery_candidates) <= 5):
            diagnostics.append(Diagnostic("discovery.candidates.count_invalid", f"Discovery-only mode requires 1 to 5 T-n candidates, found {len(assessment.discovery_candidates)}."))
        if not assessment.verifications:
            diagnostics.append(Diagnostic("discovery.only.verifications_missing", "Discovery-only mode requires at least one V-n verification record."))
        if not assessment.handoff:
            diagnostics.append(Diagnostic("discovery.only.handoff_missing", "Discovery-only mode requires exactly one H-n handoff record."))
        elif assessment.handoff.next != "codebase-issue-auditor":
            diagnostics.append(Diagnostic("discovery.only.handoff_invalid", f"Discovery-only mode handoff must be codebase-issue-auditor, got '{assessment.handoff.next}'", assessment.handoff.line_number))

        if selected_candidates:
            diagnostics.append(Diagnostic("discovery.only.selected_prohibited", f"Discovery-only mode prohibits selected candidates, found {len(selected_candidates)}.", selected_candidates[0].line_number))

        for tc in assessment.discovery_candidates:
            if tc.status not in {"rejected", "deferred"}:
                diagnostics.append(Diagnostic("discovery.only.candidate_status_invalid", f"Candidate {tc.id} status in discovery-only mode must be rejected or deferred, got '{tc.status}'", tc.line_number))
            if not tc.reason or tc.reason.strip() == "" or _is_placeholder(tc.reason) or len(tc.reason.strip()) < 10:
                diagnostics.append(Diagnostic("discovery.only.reason_missing", f"Candidate {tc.id} in discovery-only mode must state a specific refusal reason.", tc.line_number))
            for ev_id in tc.evidence:
                if ev_id not in valid_fact_ids:
                    diagnostics.append(Diagnostic("discovery.candidate.evidence_invalid", f"Candidate {tc.id} cites unknown evidence '{ev_id}'", tc.line_number))
            for aff_id in tc.affected:
                if aff_id not in valid_contract_ids:
                    diagnostics.append(Diagnostic("discovery.candidate.affected_invalid", f"Candidate {tc.id} cites unknown affected contract '{aff_id}'", tc.line_number))
            if tc.pressure and tc.pressure.lower() not in {"none", "n/a", "not-applicable", "not applicable"} and tc.pressure not in valid_pressure_ids:
                diagnostics.append(Diagnostic("discovery.candidate.pressure_invalid", f"Candidate {tc.id} cites unknown pressure '{tc.pressure}'", tc.line_number))

        if assessment.decision:
            diagnostics.append(Diagnostic("discovery.only.decision_prohibited", "Discovery-only mode prohibits D-n decision records."))
        for alt in assessment.alternatives:
            if alt.selected:
                diagnostics.append(Diagnostic("discovery.only.selected_alt_prohibited", "Discovery-only mode prohibits selected O-n alternatives.", alt.line_number))
        if assessment.pattern_gates:
            diagnostics.append(Diagnostic("discovery.only.pattern_prohibited", "Discovery-only mode prohibits G-n pattern gate records."))
        if assessment.migrations:
            diagnostics.append(Diagnostic("discovery.only.migration_prohibited", "Discovery-only mode prohibits M-n migration records."))

    # 3. Level-Specific Field Requirements & Placeholders
    if effective_level == "L1" and not is_discovery_only:
        l1_body, _ = _section(text, "Local Simplification and Preservation")
        if l1_body:
            for field_name in ("Responsibility:", "Concepts removed:", "Concepts retained:", "Preservation proof:"):
                if field_name not in l1_body:
                    diagnostics.append(Diagnostic("l1.preservation.incomplete", f"Local Simplification section missing required field '{field_name}'"))

    elif effective_level in {"L2", "L3"} and not is_discovery_only:
        tb_body, _ = _section(text, "Target Boundary")
        if tb_body:
            for field_name in ("Responsibility and owner:", "Dependency direction:", "State and contract ownership:", "Allowed calls and failures:"):
                if field_name not in tb_body:
                    diagnostics.append(Diagnostic("l2.boundary.incomplete", f"Target Boundary section missing required field '{field_name}'"))

        if not assessment.migrations:
            diagnostics.append(Diagnostic("l2.migration.missing", f"Level {effective_level} assessment requires at least one M-n migration record"))

        op_body, op_line = _section(text, "Operational Semantics")
        if op_body:
            contract_ops = contract.get("operational_fields", [])
            for op_field in contract_ops:
                pattern = rf"^-\s*{re.escape(op_field.title())}:\s*(?P<val>.*)$"
                match = re.search(pattern, op_body, re.MULTILINE | re.IGNORECASE)
                if not match:
                    diagnostics.append(Diagnostic("operational.field.missing", f"Operational Semantics missing required field '{op_field.title()}'", op_line))
                else:
                    val = match.group("val").strip()
                    val_norm = val.casefold()
                    if _is_placeholder(val) and not allow_placeholders:
                        diagnostics.append(Diagnostic("operational.placeholder.invalid", f"Operational field '{op_field.title()}' cannot use unevidenced placeholder '{val}'", op_line))
                    elif "not-applicable" in val_norm or "not applicable" in val_norm:
                        if "|" not in val or "evidence:" not in val_norm or "reason:" not in val_norm:
                            diagnostics.append(Diagnostic("operational.placeholder.invalid", f"Operational field '{op_field.title()}' not-applicable requires structured evidence and reason", op_line))
                        else:
                            ev_m = re.search(r"evidence:\s*([^\s|]+)", val, re.IGNORECASE)
                            reas_m = re.search(r"reason:\s*([^|]+)", val, re.IGNORECASE)
                            ev_id = ev_m.group(1).strip() if ev_m else ""
                            reason_str = reas_m.group(1).strip() if reas_m else ""
                            if not ev_id or ev_id not in valid_fact_ids:
                                diagnostics.append(Diagnostic("operational.evidence.invalid", f"Operational field '{op_field.title()}' cites unknown evidence '{ev_id}'", op_line))
                            if not reason_str or (_is_placeholder(reason_str) and not allow_placeholders):
                                diagnostics.append(Diagnostic("operational.reason.invalid", f"Operational field '{op_field.title()}' reason cannot be empty or placeholder", op_line))

        if effective_level == "L3":
            evo_body, evo_line = _section(text, "System Ownership and Evolution")
            if evo_body:
                contract_evo = contract.get("l3_evolution_fields", [])
                for evo_field in contract_evo:
                    pattern = rf"^-\s*{re.escape(evo_field.title())}:\s*(?P<val>.*)$"
                    match = re.search(pattern, evo_body, re.MULTILINE | re.IGNORECASE)
                    if not match:
                        diagnostics.append(Diagnostic("l3.evolution_field.missing", f"System Evolution missing required field '{evo_field.title()}'", evo_line))
                    else:
                        val = match.group("val").strip()
                        if _is_placeholder(val) and not allow_placeholders:
                            diagnostics.append(Diagnostic("l3.evolution_placeholder.invalid", f"System Evolution field '{evo_field.title()}' cannot use unevidenced placeholder '{val}'", evo_line))

    # 4. Decision Summary Consistency Validation
    if assessment.decision_summary:
        ds = assessment.decision_summary
        if ds.mode and ds.mode != expected_mode:
            diagnostics.append(Diagnostic("summary.mode.mismatch", f"Decision Summary mode '{ds.mode}' != assessment mode '{expected_mode}'"))
        if ds.level and ds.level != effective_level:
            diagnostics.append(Diagnostic("summary.level.mismatch", f"Decision Summary level '{ds.level}' != declared level '{effective_level}'"))
        if ds.next_owner and assessment.handoff and ds.next_owner != assessment.handoff.next:
            diagnostics.append(Diagnostic("summary.next_owner.mismatch", f"Decision Summary next_owner '{ds.next_owner}' != Handoff next '{assessment.handoff.next}'"))

        if not is_discovery_only and assessment.decision:
            d_id = assessment.decision.design_id
            if d_id and not _is_placeholder(d_id):
                if ds.selected_design_id and ds.selected_design_id != d_id:
                    diagnostics.append(Diagnostic("summary.design_id.mismatch", f"Decision Summary selected design-id '{ds.selected_design_id}' != D-n design-id '{d_id}'"))

        if ds.protected_contracts and assessment.contracts:
            c_refs = [c.strip().split()[0] for c in ds.protected_contracts.split(",") if c.strip()]
            for c_ref in c_refs:
                if c_ref.startswith("C-") and c_ref not in valid_contract_ids:
                    diagnostics.append(Diagnostic("summary.contract.invalid", f"Decision Summary protected contract '{c_ref}' not found in C-n records"))

        if ds.primary_pressure and assessment.pressures:
            p_refs = [p.strip().split()[0] for p in ds.primary_pressure.split(",") if p.strip()]
            for p_ref in p_refs:
                if p_ref.startswith("P-") and p_ref not in valid_pressure_ids:
                    diagnostics.append(Diagnostic("summary.pressure.invalid", f"Decision Summary primary pressure '{p_ref}' not found in P-n records"))

        if ds.debt_disposition and assessment.tech_debts:
            valid_disps = {td.disposition for td in assessment.tech_debts}
            parsed_ds_disp = ds.debt_disposition.split(":", 1)[-1].strip() if ":" in ds.debt_disposition else ds.debt_disposition.strip()
            parsed_ds_disp = parsed_ds_disp.split()[0]
            if parsed_ds_disp in VALID_DEBT_DISPOSITIONS and parsed_ds_disp not in valid_disps:
                diagnostics.append(Diagnostic("summary.debt_disposition.mismatch", f"Decision Summary debt disposition '{parsed_ds_disp}' not found among TD-n dispositions {valid_disps}"))

        if ds.residual_risk and assessment.residual_risks:
            r_refs = [r.strip().split()[0] for r in ds.residual_risk.split(",") if r.strip()]
            for r_ref in r_refs:
                if r_ref.startswith("R-") and r_ref not in valid_risk_ids:
                    diagnostics.append(Diagnostic("summary.risk.invalid", f"Decision Summary residual risk '{r_ref}' not found in R-n records"))

    # 5. Fact Verification (Path bounds, line count, anchor, git history)
    root = repo_root.resolve()
    has_git = (root / ".git").is_dir()

    for f in assessment.facts:
        if f.source not in VALID_SOURCES:
            diagnostics.append(Diagnostic("fact.source.invalid", f"Fact {f.id} has invalid source '{f.source}'", f.line_number))
        if f.strength not in VALID_STRENGTHS:
            diagnostics.append(Diagnostic("fact.strength.invalid", f"Fact {f.id} has invalid strength '{f.strength}'", f.line_number))
        if f.freshness not in VALID_FRESHNESS:
            diagnostics.append(Diagnostic("fact.freshness.invalid", f"Fact {f.id} has invalid freshness '{f.freshness}'", f.line_number))

        if f.source == "repository-history":
            if not f.path.startswith("git-history:"):
                diagnostics.append(Diagnostic("fact.git_history.format_invalid", f"Fact {f.id} with repository-history source must use git-history:<commit-sha>:<repository-path>:<line> format", f.line_number))

        if f.path.startswith("git-history:"):
            gh_match = re.match(r"^git-history:(?P<sha>[0-9a-fA-F]{4,40}):(?P<path>[^\s:]+)(?::(?P<line>\d+))?$", f.path)
            if not gh_match:
                diagnostics.append(Diagnostic("fact.git_history.malformed", f"Fact {f.id} has malformed git-history locator '{f.path}'", f.line_number))
            elif not has_git:
                diagnostics.append(Diagnostic("fact.git_history.git_unavailable", f"Repository is not a Git checkout; cannot verify historical fact {f.id}", f.line_number))
            else:
                commit_sha = gh_match.group("sha")
                rel_path = gh_match.group("path")
                line_val = int(gh_match.group("line")) if gh_match.group("line") else f.line

                if rel_path.startswith("/") or rel_path.startswith("\\") or ".." in Path(rel_path).parts:
                    diagnostics.append(Diagnostic("fact.path.traversal", f"Fact {f.id} historical path '{rel_path}' escapes repository root", f.line_number))
                else:
                    c_check = subprocess.run(["git", "rev-parse", "--verify", f"{commit_sha}^{{commit}}"], cwd=root, capture_output=True)
                    if c_check.returncode != 0:
                        diagnostics.append(Diagnostic("fact.git_history.commit_missing", f"Fact {f.id} git commit '{commit_sha}' does not exist in repository", f.line_number))
                    else:
                        f_check = subprocess.run(["git", "cat-file", "-e", f"{commit_sha}:{rel_path}"], cwd=root, capture_output=True)
                        if f_check.returncode != 0:
                            diagnostics.append(Diagnostic("fact.git_history.file_missing", f"Fact {f.id} file '{rel_path}' does not exist at commit '{commit_sha}'", f.line_number))
                        else:
                            content_res = subprocess.run(["git", "show", f"{commit_sha}:{rel_path}"], cwd=root, capture_output=True, text=True, errors="replace")
                            if content_res.returncode == 0:
                                hist_lines = content_res.stdout.splitlines()
                                if line_val < 1 or line_val > max(1, len(hist_lines)):
                                    diagnostics.append(Diagnostic("fact.line.out_of_bounds", f"Fact {f.id} line {line_val} exceeds historical file bounds ({len(hist_lines)})", f.line_number))
                                else:
                                    if not f.anchor or not f.anchor.strip():
                                        if not allow_placeholders:
                                            diagnostics.append(Diagnostic("fact.anchor.empty", f"Fact {f.id} anchor cannot be empty", f.line_number))
                                    elif _is_placeholder(f.anchor):
                                        if not allow_placeholders:
                                            diagnostics.append(Diagnostic("fact.anchor.placeholder", f"Fact {f.id} anchor cannot use placeholder '{f.anchor}'", f.line_number))
                                    else:
                                        start_l = max(0, line_val - 1 - 10)
                                        end_l = min(len(hist_lines), line_val + 10)
                                        window_text = "\n".join(hist_lines[start_l:end_l])
                                        if f.anchor not in window_text:
                                            diagnostics.append(Diagnostic("fact.anchor.missing", f"Fact {f.id} anchor '{f.anchor}' not found near line {line_val} in historical {rel_path}", f.line_number))

        elif f.source not in {"fixture"}:
            if f.path.startswith("/") or f.path.startswith("\\") or ".." in Path(f.path).parts:
                diagnostics.append(Diagnostic("fact.path.traversal", f"Fact {f.id} path '{f.path}' escapes repository root", f.line_number))
            else:
                fact_file = root / f.path.split(":")[0]
                if not fact_file.is_file():
                    if not allow_placeholders:
                        diagnostics.append(Diagnostic("fact.path.missing", f"Fact {f.id} path '{f.path}' does not exist on disk", f.line_number))
                else:
                    file_lines = fact_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    if f.line < 1 or f.line > max(1, len(file_lines)):
                        diagnostics.append(Diagnostic("fact.line.out_of_bounds", f"Fact {f.id} line {f.line} exceeds file bounds ({len(file_lines)})", f.line_number))

                    if not f.anchor or not f.anchor.strip():
                        if not allow_placeholders:
                            diagnostics.append(Diagnostic("fact.anchor.empty", f"Fact {f.id} anchor cannot be empty", f.line_number))
                    elif _is_placeholder(f.anchor):
                        if not allow_placeholders:
                            diagnostics.append(Diagnostic("fact.anchor.placeholder", f"Fact {f.id} anchor cannot use placeholder '{f.anchor}'", f.line_number))
                    else:
                        start_l = max(0, f.line - 1 - 10)
                        end_l = min(len(file_lines), f.line + 10)
                        window_text = "\n".join(file_lines[start_l:end_l])
                        if f.anchor not in window_text:
                            diagnostics.append(Diagnostic("fact.anchor.missing", f"Fact {f.id} anchor '{f.anchor}' not found near line {f.line} in {f.path}", f.line_number))

    for ef in assessment.external_facts:
        if ef.freshness not in VALID_FRESHNESS:
            diagnostics.append(Diagnostic("fact.freshness.invalid", f"External fact {ef.id} has invalid freshness '{ef.freshness}'", ef.line_number))

    # 6. L2/L3 Evidence Checks
    if effective_level in {"L2", "L3"} and not is_discovery_only:
        valid_facts = [f for f in assessment.facts if f.source in VALID_SOURCES]
        sources_used = {f.source for f in valid_facts}

        if effective_level == "L3" and not allow_placeholders:
            if len(sources_used) < 3:
                diagnostics.append(Diagnostic("evidence.l3.categories_insufficient", f"L3 assessment requires at least 3 distinct evidence categories, found {len(sources_used)} ({sources_used})"))

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

    # 7. Pressure Validation
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

    # 8. Contract Validation
    for c in assessment.contracts:
        if c.status == "authorized-change" and (not c.authorization or c.authorization == "none"):
            diagnostics.append(Diagnostic("contract.authorization.missing", f"Contract {c.id} with authorized-change must name explicit authorization", c.line_number))
        elif c.status == "at-risk":
            if not c.owner or not c.resolution:
                diagnostics.append(Diagnostic("contract.at_risk.incomplete", f"Contract {c.id} at-risk must specify owner and resolution", c.line_number))
            if c.blocking:
                diagnostics.append(Diagnostic("contract.at_risk.unresolved", f"Contract {c.id} remains unresolved blocking contract", c.line_number))

    # 9. Decision & Alternatives Validation (including design-id matching)
    if assessment.decision and not is_discovery_only:
        d = assessment.decision
        if d.level != effective_level:
            diagnostics.append(Diagnostic("decision.level.mismatch", f"Decision level {d.level} != declared level {effective_level}", d.line_number))
        if not d.design_id or (_is_placeholder(d.design_id) and not allow_placeholders):
            diagnostics.append(Diagnostic("decision.design_id.missing", f"Decision {d.id} requires structured non-placeholder design-id", d.line_number))
        if not d.because:
            diagnostics.append(Diagnostic("decision.because.missing", f"Decision {d.id} must cite facts/pressures in because", d.line_number))
        else:
            has_fact = any(b in valid_fact_ids for b in d.because)
            has_pressure = any(b in valid_pressure_ids for b in d.because)
            if not has_fact or not has_pressure:
                diagnostics.append(Diagnostic("decision.because.invalid", f"Decision {d.id} because must cite at least one fact (F-n/E-n) AND at least one pressure (P-n)", d.line_number))
            for b_id in d.because:
                if b_id not in valid_fact_ids and b_id not in valid_pressure_ids:
                    diagnostics.append(Diagnostic("decision.because.unknown_id", f"Decision {d.id} because cites unknown ID '{b_id}'", d.line_number))

        if not d.rejected or (_is_placeholder(d.rejected) and not allow_placeholders):
            diagnostics.append(Diagnostic("decision.rejected.missing", f"Decision {d.id} must explain why lower level was rejected", d.line_number))

        selected_alts = [a for a in assessment.alternatives if a.selected]
        if len(selected_alts) != 1:
            diagnostics.append(Diagnostic("alternatives.selected.count_invalid", f"Exactly one selected O-n alternative required, found {len(selected_alts)}."))
        else:
            sel_alt = selected_alts[0]
            if sel_alt.level != d.level:
                diagnostics.append(Diagnostic("alternatives.selected.level_mismatch", f"Selected alternative O-n level {sel_alt.level} != D-n level {d.level}", sel_alt.line_number))
            if not sel_alt.design_id or (_is_placeholder(sel_alt.design_id) and not allow_placeholders):
                diagnostics.append(Diagnostic("alternatives.selected.design_id_missing", f"Selected alternative {sel_alt.id} requires structured non-placeholder design-id", sel_alt.line_number))
            elif d.design_id and sel_alt.design_id != d.design_id:
                diagnostics.append(Diagnostic("alternatives.selected.design_id_mismatch", f"Selected alternative design-id '{sel_alt.design_id}' != D-n design-id '{d.design_id}'", sel_alt.line_number))

        alt_design_ids = [a.design_id for a in assessment.alternatives if a.design_id and not _is_placeholder(a.design_id)]
        if len(alt_design_ids) != len(set(alt_design_ids)):
            diagnostics.append(Diagnostic("alternatives.design_id.duplicate", "Alternatives must have unique design-id values"))

        if effective_level in {"L2", "L3"}:
            has_lower = any(a.level in {"L0", "L1"} for a in assessment.alternatives)
            if not has_lower:
                diagnostics.append(Diagnostic("alternatives.l2_l3.lower_level_missing", f"{effective_level} assessment must include L0 or L1 alternative"))

    # 10. Pattern Gate Validation
    valid_pattern_scopes = set(contract.get("pattern_scopes", ["introduced", "removed", "retained", "rejected", "deferred", "relied-upon"]))
    valid_pattern_results = set(contract.get("pattern_results", ["admit", "admit-narrowed", "retain", "remove", "reject", "defer"]))

    for g in assessment.pattern_gates:
        if not g.pattern or (_is_placeholder(g.pattern) and not allow_placeholders):
            diagnostics.append(Diagnostic("pattern.name.missing", f"Pattern gate {g.id} requires pattern name", g.line_number))
        if g.scope not in valid_pattern_scopes:
            diagnostics.append(Diagnostic("pattern.scope.invalid", f"Pattern gate {g.id} has invalid scope '{g.scope}'", g.line_number))
        if g.result not in valid_pattern_results:
            diagnostics.append(Diagnostic("pattern.result.invalid", f"Pattern gate {g.id} has invalid result '{g.result}'", g.line_number))

        if g.evidence:
            for ev_id in g.evidence:
                if ev_id not in valid_fact_ids and ev_id not in valid_pressure_ids and ev_id not in valid_contract_ids:
                    diagnostics.append(Diagnostic("pattern.evidence.invalid", f"Pattern gate {g.id} cites unknown evidence ID '{ev_id}'", g.line_number))
        else:
            diagnostics.append(Diagnostic("pattern.evidence.missing", f"Pattern gate {g.id} requires evidence citation", g.line_number))

        if not g.questions or len(g.questions) < 14:
            diagnostics.append(Diagnostic("pattern.questions.missing", f"Pattern gate {g.id} must include all structured Q1-Q14 gate questions", g.line_number))
        else:
            for q_num in range(1, 15):
                if q_num not in g.questions:
                    diagnostics.append(Diagnostic("pattern.hard_gate.missing", f"Pattern gate {g.id} requires question Q{q_num}", g.line_number))
                else:
                    qa = g.questions[q_num]
                    if qa.answer not in {"yes", "no", "unknown"}:
                        diagnostics.append(Diagnostic("pattern.answer.invalid", f"Pattern gate {g.id} Q{q_num} invalid answer '{qa.answer}'", g.line_number))
                    if not qa.evidence:
                        diagnostics.append(Diagnostic("pattern.evidence.missing", f"Pattern gate {g.id} Q{q_num} requires evidence citation", g.line_number))
                    else:
                        for q_ev_id in qa.evidence:
                            if q_ev_id not in valid_fact_ids and q_ev_id not in valid_pressure_ids and q_ev_id not in valid_contract_ids:
                                diagnostics.append(Diagnostic("pattern.evidence.invalid", f"Pattern gate {g.id} Q{q_num} cites unknown evidence '{q_ev_id}'", q_num))
                    if not qa.consequence or (_is_placeholder(qa.consequence) and not allow_placeholders):
                        diagnostics.append(Diagnostic("pattern.consequence.missing", f"Pattern gate {g.id} Q{q_num} requires non-placeholder consequence", q_num))

            if g.result in {"admit", "admit-narrowed"}:
                for hard_q in HARD_PATTERN_QUESTIONS:
                    if hard_q in g.questions and g.questions[hard_q].answer != "yes":
                        diagnostics.append(Diagnostic("pattern.hard_gate.failed", f"Pattern gate {g.id} result '{g.result}' requires Q{hard_q}=yes, got '{g.questions[hard_q].answer}'", g.line_number))

        if g.scope == "removed" or g.result == "remove":
            if not g.removed_destination or (_is_placeholder(g.removed_destination) and not allow_placeholders):
                diagnostics.append(Diagnostic("pattern.removal.destination_missing", f"Pattern removal {g.id} must state removed-destination", g.line_number))
        if g.result == "defer" and (not g.revisit_trigger or (_is_placeholder(g.revisit_trigger) and not allow_placeholders)):
            diagnostics.append(Diagnostic("pattern.defer.revisit_missing", f"Pattern deferral {g.id} must specify revisit-trigger", g.line_number))

    # 11. Grounded Technical Debt Validation
    valid_debt_frequencies = set(contract.get("debt_frequencies", ["current", "recurring", "historical", "unknown"]))
    for td in assessment.tech_debts:
        if td.type not in VALID_DEBT_TYPES:
            diagnostics.append(Diagnostic("tech_debt.type.invalid", f"Technical debt {td.id} invalid type '{td.type}'", td.line_number))
        if td.disposition not in VALID_DEBT_DISPOSITIONS:
            diagnostics.append(Diagnostic("tech_debt.disposition.invalid", f"Technical debt {td.id} invalid disposition '{td.disposition}'", td.line_number))
        if td.frequency not in valid_debt_frequencies:
            diagnostics.append(Diagnostic("tech_debt.frequency.invalid", f"Technical debt {td.id} invalid frequency '{td.frequency}'", td.line_number))

        if not td.evidence:
            diagnostics.append(Diagnostic("tech_debt.evidence.missing", f"Technical debt {td.id} requires at least one valid F-n or E-n evidence citation", td.line_number))
        else:
            for ev_id in td.evidence:
                if ev_id not in valid_fact_ids:
                    diagnostics.append(Diagnostic("tech_debt.evidence.invalid", f"Technical debt {td.id} cites unknown evidence '{ev_id}'", td.line_number))

        for fld_name, fld_val in [
            ("principal", td.principal),
            ("interest", td.interest),
            ("frequency", td.frequency),
            ("blast-radius", td.blast_radius),
            ("reason", td.reason),
        ]:
            if not fld_val or (_is_placeholder(fld_val) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.field.missing", f"Technical debt {td.id} field '{fld_name}' cannot be empty or placeholder", td.line_number))

        if _is_superficial_debt_claim(td.principal, td.reason):
            diagnostics.append(Diagnostic("tech_debt.superficial_claim", f"Technical debt {td.id} claim is superficial; must describe evidenced structural/operational cost", td.line_number))

        if td.disposition in {"repay", "retire"}:
            if not td.repayment_boundary or (_is_placeholder(td.repayment_boundary) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.repayment_boundary.missing", f"Technical debt {td.id} disposition '{td.disposition}' requires repayment-boundary", td.line_number))
            if not td.recurrence_guard or (_is_placeholder(td.recurrence_guard) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.recurrence_guard.missing", f"Technical debt {td.id} disposition '{td.disposition}' requires recurrence-guard", td.line_number))
        elif td.disposition == "contain":
            if not td.containment_boundary or (_is_placeholder(td.containment_boundary) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.containment_boundary.missing", f"Technical debt {td.id} disposition contain requires containment-boundary", td.line_number))
            if not td.revisit_trigger or (_is_placeholder(td.revisit_trigger) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.revisit_trigger.missing", f"Technical debt {td.id} disposition contain requires revisit-trigger", td.line_number))
        elif td.disposition in {"accept", "monitor"}:
            if not td.revisit_trigger or (_is_placeholder(td.revisit_trigger) and not allow_placeholders):
                diagnostics.append(Diagnostic("tech_debt.revisit_trigger.missing", f"Technical debt {td.id} disposition '{td.disposition}' requires revisit-trigger", td.line_number))

    # 12. Verification Record Validation
    allowed_proves_types = {"D-", "T-", "C-", "TD-", "P-", "G-", "M-", "O-"}
    for v in assessment.verifications:
        if not v.proves:
            diagnostics.append(Diagnostic("verification.proves.missing", f"Verification {v.id} must state proves", v.line_number))
        else:
            for p_item in v.proves:
                if p_item.startswith("V-") or p_item.startswith("H-") or p_item.startswith("F-") or p_item.startswith("E-"):
                    diagnostics.append(Diagnostic("verification.proves.invalid_type", f"Verification {v.id} cannot prove self/handoff/fact '{p_item}'", v.line_number))
                elif not any(p_item.startswith(pt) for pt in allowed_proves_types) or p_item not in valid_record_ids:
                    diagnostics.append(Diagnostic("verification.proves.invalid", f"Verification {v.id} proves unknown or unapproved claim record '{p_item}'", v.line_number))
        if not v.method or (_is_placeholder(v.method) and not allow_placeholders) or not v.expected or (_is_placeholder(v.expected) and not allow_placeholders):
            diagnostics.append(Diagnostic("verification.method_expected.missing", f"Verification {v.id} requires concrete method and expected result", v.line_number))

    # 13. Migration Validation
    for m in assessment.migrations:
        if not m.prerequisite or (_is_placeholder(m.prerequisite) and not allow_placeholders):
            diagnostics.append(Diagnostic("migration.prerequisite.missing", f"Migration {m.id} requires concrete prerequisite", m.line_number))
        if not m.changed_boundary or (_is_placeholder(m.changed_boundary) and not allow_placeholders):
            diagnostics.append(Diagnostic("migration.changed_boundary.missing", f"Migration {m.id} requires concrete changed-boundary", m.line_number))
        if not m.preserved:
            diagnostics.append(Diagnostic("migration.preserved.missing", f"Migration {m.id} requires preserved contracts", m.line_number))
        else:
            for p_id in m.preserved:
                if not p_id.startswith("C-") or p_id not in valid_contract_ids:
                    diagnostics.append(Diagnostic("migration.preserved.invalid", f"Migration {m.id} preserved '{p_id}' must be a valid C-n contract", m.line_number))
        if not m.proof:
            diagnostics.append(Diagnostic("migration.proof.missing", f"Migration {m.id} requires proof verifications", m.line_number))
        else:
            for pr_id in m.proof:
                if not pr_id.startswith("V-") or pr_id not in valid_record_ids:
                    diagnostics.append(Diagnostic("migration.proof.invalid", f"Migration {m.id} proof '{pr_id}' must be a valid V-n verification", m.line_number))
        if not m.rollback_trigger or (_is_placeholder(m.rollback_trigger) and not allow_placeholders) or not m.rollback_action or (_is_placeholder(m.rollback_action) and not allow_placeholders):
            diagnostics.append(Diagnostic("migration.rollback.missing", f"Migration {m.id} requires concrete rollback trigger and action", m.line_number))
        if not m.cleanup or (_is_placeholder(m.cleanup) and not allow_placeholders):
            diagnostics.append(Diagnostic("migration.cleanup.missing", f"Migration {m.id} requires cleanup steps with observable completion criteria", m.line_number))

    # 14. Handoff Validation
    if assessment.handoff:
        h = assessment.handoff
        if h.next not in VALID_HANDOFFS:
            diagnostics.append(Diagnostic("handoff.next.invalid", f"Handoff next '{h.next}' must be one of {sorted(VALID_HANDOFFS)}", h.line_number))
        if assessment.decision_summary and assessment.decision_summary.next_owner:
            if assessment.decision_summary.next_owner != h.next:
                diagnostics.append(Diagnostic("summary.next_owner.mismatch", f"Decision Summary next_owner '{assessment.decision_summary.next_owner}' != Handoff next '{h.next}'", h.line_number))
        if h.next == "implement-with-senior-dev":
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
