"""Build plan-with-senior-dev skill architecture diagram."""
import re, json
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "html-excalidraw-template.html"
OUTPUT = Path(r"C:\Users\Akshay Diwadkar\.agents\skills\plan-with-senior-dev\plan-with-senior-dev-skill-architecture.html")

diagram_data = r'''
const DIAGRAM_DATA = {
  title: "Plan With Senior Dev — Skill Architecture",
  storageKey: "plan-with-senior-dev-architecture-v1",
  audience: "Agent-authors extending the skill, engineers invoking it, reviewers evaluating plan quality",
  purpose: "Explain the 4-phase lifecycle (Explore -> Grill -> Plan -> Verify), risk-tier branching, conditional reference loading, and quality gates",
  fidelity: "narrative-architecture",
  takeaways: [
    "Explore -> Grill -> Plan -> Verify is the canonical flow with feedback loops at exit-criteria, quality, and verification gates",
    "Task tier (Tiny / Standard / High-Risk) controls plan template, pre-mortem depth, and rollback detail",
    "Six reference protocols are loaded by task risk; pre-mortem and anti-patterns apply only at higher tiers"
  ],
  walkthrough: [
    {
      id: "request",
      title: "Request arrives",
      description: "User brings an ambiguous implementation request. Agent checks the codebase and domain docs for existing context.",
      nodeIds: ["user", "codebase", "domain-docs", "explore"]
    },
    {
      id: "explore",
      title: "Phase 1: Explore",
      description: "Agent builds current-state evidence from entrypoints, call paths, analogous patterns, tests, and config, loading reference protocols conditionally.",
      nodeIds: ["explore", "ref-files"]
    },
    {
      id: "grill",
      title: "Phase 2: Grill to Shared Understanding",
      description: "Design-tree walk: one question at a time with recommendation + why-it-matters format, probing concrete scenarios until all exit criteria are met.",
      nodeIds: ["grill", "exit-gate"]
    },
    {
      id: "tier-select",
      title: "Task tier selection",
      description: "Exit criteria met. Route by risk: Tiny for local changes, Standard for default work, High-Risk for data/contracts/payments. Pre-mortem runs for Standard and High-Risk.",
      nodeIds: ["tier-gate", "premortem"]
    },
    {
      id: "plan-gen",
      title: "Phase 3: Plan Generation",
      description: "Write dependency-ordered, decision-complete plan. Validate structure and rubric via scripts/check_plan.py before proceeding.",
      nodeIds: ["plan", "quality-gate"]
    },
    {
      id: "verify",
      title: "Phase 4: Verify and Deliver",
      description: "Check claims, scope, failure modes, tests, rollback, and domain terms. If all pass, deliver the final decision-complete plan artifact to the user.",
      nodeIds: ["verify", "plan-out", "user"]
    }
  ],
  nodes: [
    { id: "user", label: "User / Requester", type: "actor", description: "Brings an ambiguous implementation request that needs a decision-complete plan" },
    { id: "codebase", label: "Target Codebase", type: "file", description: "The repo explored for current-state evidence: entrypoints, call paths, tests, config" },
    { id: "domain-docs", label: "Domain Docs", type: "document", description: "CONTEXT.md glossary and ADRs for durable tradeoffs, checked before planning" },
    { id: "explore", label: "Explore Phase", type: "process", description: "Phase 1: reads entrypoints, call paths, analogous patterns, tests, config, and contradictions" },
    { id: "ref-files", label: "Reference Protocols", type: "file", description: "Six conditional guides: exploration, questions, grilling, rubric, pre-mortem, anti-patterns" },
    { id: "grill", label: "Grill to Shared Understanding", type: "process", description: "Phase 2: design-tree walk with recommendation + why-it-matters format, one question at a time" },
    { id: "exit-gate", label: "Exit Criteria Gate", type: "decision", description: "All criteria met? Goals concrete, terms agreed, interfaces decided, edge cases settled" },
    { id: "tier-gate", label: "Task Tier Decision", type: "decision", description: "Routes Tiny (local/reversible), Standard (default multi-layer), or High-Risk (data/contracts)" },
    { id: "premortem", label: "Pre-Mortem Protocol", type: "process", description: "Risk analysis for Standard & High-Risk: scope, data, performance, integration, rollback traps" },
    { id: "plan", label: "Plan Generator", type: "process", description: "Phase 3: produces dependency-ordered, decision-complete plan following local patterns" },
    { id: "quality-gate", label: "Quality Rubric Check", type: "decision", description: "Validates plan via scripts/check_plan.py: shape, rubric, deferred decisions, hedging language" },
    { id: "verify", label: "Verify Phase", type: "process", description: "Phase 4: checks claims, scope, failure modes, tests, rollback, and domain term alignment" },
    { id: "plan-out", label: "Decision-Complete Plan", type: "document", description: "Final artifact ready for implementation by another engineer or agent without further decisions" }
  ],
  edges: [
    { sourceId: "user", targetId: "explore", label: "triggers", evidence: "user-stated", confidence: "stated" },
    { sourceId: "explore", targetId: "codebase", label: "reads evidence", evidence: "SKILL.md:46-57", confidence: "observed" },
    { sourceId: "explore", targetId: "domain-docs", label: "checks glossary", evidence: "SKILL.md:50", confidence: "observed" },
    { sourceId: "explore", targetId: "ref-files", label: "loads conditionally", evidence: "SKILL.md:14-21", confidence: "inferred" },
    { sourceId: "explore", targetId: "grill", label: "proceeds to", evidence: "SKILL.md:60", confidence: "observed" },
    { sourceId: "grill", targetId: "exit-gate", label: "evaluates criteria", evidence: "SKILL.md:80-91", confidence: "observed" },
    { sourceId: "exit-gate", targetId: "grill", label: "criteria not met", evidence: "SKILL.md:92", confidence: "observed" },
    { sourceId: "exit-gate", targetId: "tier-gate", label: "criteria met", evidence: "SKILL.md:92", confidence: "observed" },
    { sourceId: "tier-gate", targetId: "premortem", label: "standard/high-risk", evidence: "SKILL.md:106-107", confidence: "observed" },
    { sourceId: "tier-gate", targetId: "plan", label: "tiny route", evidence: "SKILL.md:125-148", confidence: "observed" },
    { sourceId: "premortem", targetId: "plan", label: "informs", evidence: "pre-mortem.md:3-4", confidence: "observed" },
    { sourceId: "plan", targetId: "quality-gate", label: "validates via script", evidence: "SKILL.md:67-81", confidence: "observed" },
    { sourceId: "quality-gate", targetId: "plan", label: "check failed", evidence: "SKILL.md:121", confidence: "observed" },
    { sourceId: "quality-gate", targetId: "verify", label: "check passed", evidence: "SKILL.md:110", confidence: "observed" },
    { sourceId: "verify", targetId: "explore", label: "check failed", evidence: "SKILL.md:121", confidence: "observed" },
    { sourceId: "verify", targetId: "plan-out", label: "passes all checks", evidence: "user-stated", confidence: "stated" },
    { sourceId: "plan-out", targetId: "user", label: "delivers", evidence: "user-stated", confidence: "stated" }
  ],
  clusters: [
    { id: "c-inputs", label: "Inputs", nodeIds: ["user", "codebase", "domain-docs"] },
    { id: "c-explore", label: "Phase 1: Explore", nodeIds: ["explore", "ref-files"] },
    { id: "c-grill", label: "Phase 2: Grill", nodeIds: ["grill", "exit-gate"] },
    { id: "c-plan", label: "Phase 3: Plan", nodeIds: ["tier-gate", "premortem", "plan"] },
    { id: "c-verify", label: "Phase 4: Verify", nodeIds: ["quality-gate", "verify"] },
    { id: "c-output", label: "Output", nodeIds: ["plan-out"] }
  ]
};
'''

agent_metadata = {
    "audience": "Agent-authors extending the skill, engineers invoking it, reviewers evaluating plan quality",
    "purpose": "Explain the 4-phase lifecycle (Explore -> Grill -> Plan -> Verify), risk-tier branching, conditional reference loading, and quality gates",
    "fidelity": "narrative-architecture",
    "entities": [
        {"id": "user", "name": "User / Requester", "type": "actor", "description": "Brings an ambiguous implementation request that needs a decision-complete plan", "evidence": "user-stated"},
        {"id": "codebase", "name": "Target Codebase", "type": "file", "description": "The repo explored for current-state evidence: entrypoints, call paths, tests, config", "evidence": "SKILL.md:46-57"},
        {"id": "domain-docs", "name": "Domain Docs", "type": "document", "description": "CONTEXT.md glossary and ADRs for durable tradeoffs, checked before planning", "evidence": "SKILL.md:50"},
        {"id": "explore", "name": "Explore Phase", "type": "process", "description": "Phase 1: reads entrypoints, call paths, analogous patterns, tests, config, and contradictions", "evidence": "SKILL.md:44-58"},
        {"id": "ref-files", "name": "Reference Protocols", "type": "file", "description": "Six conditionally-loaded guides: exploration, questions, grilling, rubric, pre-mortem, anti-patterns", "evidence": "SKILL.md:14-21"},
        {"id": "grill", "name": "Grill to Shared Understanding", "type": "process", "description": "Phase 2: design-tree walk with recommendation + why-it-matters format, one question at a time", "evidence": "SKILL.md:60-92"},
        {"id": "exit-gate", "name": "Exit Criteria Gate", "type": "decision", "description": "All criteria met? Goals concrete, terms agreed, interfaces decided, edge cases settled", "evidence": "SKILL.md:80-92"},
        {"id": "tier-gate", "name": "Task Tier Decision", "type": "decision", "description": "Routes Tiny (local/reversible), Standard (default multi-layer), or High-Risk (data/contracts)", "evidence": "SKILL.md:123-187"},
        {"id": "premortem", "name": "Pre-Mortem Protocol", "type": "process", "description": "Risk analysis for Standard & High-Risk: scope, data, performance, integration, rollback traps", "evidence": "pre-mortem.md"},
        {"id": "plan", "name": "Plan Generator", "type": "process", "description": "Phase 3: produces dependency-ordered, decision-complete plan following local patterns", "evidence": "SKILL.md:94-108"},
        {"id": "quality-gate", "name": "Quality Rubric Check", "type": "decision", "description": "Validates plan via scripts/check_plan.py: shape, rubric, deferred decisions, hedging language", "evidence": "SKILL.md:67-81"},
        {"id": "verify", "name": "Verify Phase", "type": "process", "description": "Phase 4: checks claims, scope, failure modes, tests, rollback, and domain term alignment", "evidence": "SKILL.md:108-121"},
        {"id": "plan-out", "name": "Decision-Complete Plan", "type": "document", "description": "Final artifact ready for implementation by another engineer or agent without further decisions", "evidence": "SKILL.md:94-108"}
    ],
    "relationships": [
        {"sourceId": "user", "targetId": "explore", "label": "triggers", "direction": "User -> Explore Phase", "confidence": "stated", "evidence": "user-stated"},
        {"sourceId": "explore", "targetId": "codebase", "label": "reads evidence", "direction": "Explore Phase -> Target Codebase", "confidence": "observed", "evidence": "SKILL.md:46-57"},
        {"sourceId": "explore", "targetId": "domain-docs", "label": "checks glossary", "direction": "Explore Phase -> Domain Docs", "confidence": "observed", "evidence": "SKILL.md:50"},
        {"sourceId": "explore", "targetId": "ref-files", "label": "loads conditionally", "direction": "Explore Phase -> Reference Protocols", "confidence": "inferred", "evidence": "SKILL.md:14-21"},
        {"sourceId": "explore", "targetId": "grill", "label": "proceeds to", "direction": "Explore Phase -> Grill to Shared Understanding", "confidence": "observed", "evidence": "SKILL.md:60"},
        {"sourceId": "grill", "targetId": "exit-gate", "label": "evaluates criteria", "direction": "Grill -> Exit Criteria Gate", "confidence": "observed", "evidence": "SKILL.md:80-91"},
        {"sourceId": "exit-gate", "targetId": "grill", "label": "criteria not met", "direction": "Exit Criteria Gate -> Grill", "confidence": "observed", "evidence": "SKILL.md:92"},
        {"sourceId": "exit-gate", "targetId": "tier-gate", "label": "criteria met", "direction": "Exit Criteria Gate -> Task Tier Decision", "confidence": "observed", "evidence": "SKILL.md:92"},
        {"sourceId": "tier-gate", "targetId": "premortem", "label": "standard/high-risk", "direction": "Task Tier Decision -> Pre-Mortem Protocol", "confidence": "observed", "evidence": "SKILL.md:106-107"},
        {"sourceId": "tier-gate", "targetId": "plan", "label": "tiny route", "direction": "Task Tier Decision -> Plan Generator", "confidence": "observed", "evidence": "SKILL.md:125-148"},
        {"sourceId": "premortem", "targetId": "plan", "label": "informs", "direction": "Pre-Mortem Protocol -> Plan Generator", "confidence": "observed", "evidence": "pre-mortem.md:3-4"},
        {"sourceId": "plan", "targetId": "quality-gate", "label": "validates via script", "direction": "Plan Generator -> Quality Rubric Check", "confidence": "observed", "evidence": "SKILL.md:67-81"},
        {"sourceId": "quality-gate", "targetId": "plan", "label": "check failed", "direction": "Quality Rubric Check -> Plan Generator", "confidence": "observed", "evidence": "SKILL.md:121"},
        {"sourceId": "quality-gate", "targetId": "verify", "label": "check passed", "direction": "Quality Rubric Check -> Verify Phase", "confidence": "observed", "evidence": "SKILL.md:110"},
        {"sourceId": "verify", "targetId": "explore", "label": "check failed", "direction": "Verify Phase -> Explore Phase", "confidence": "observed", "evidence": "SKILL.md:121"},
        {"sourceId": "verify", "targetId": "plan-out", "label": "passes all checks", "direction": "Verify Phase -> Decision-Complete Plan", "confidence": "stated", "evidence": "user-stated"},
        {"sourceId": "plan-out", "targetId": "user", "label": "delivers", "direction": "Decision-Complete Plan -> User", "confidence": "stated", "evidence": "user-stated"}
    ],
    "assumptions": [
        "Scripts directory internals (check_plan_shape.py, check_plan_rubric.py, _plan_utils.py) are collapsed into Quality Rubric Check node",
        "All six reference files (exploration, question, grilling, rubric, pre-mortem, anti-patterns) are grouped into one Reference Protocols node",
        "The OpenAI agent config (agents/openai.yaml) is out of scope",
        "Domain docs are updated inline during the Grill and Plan phases; not shown as a separate output"
    ],
    "omissions": [
        "Individual script file paths and line-level evidence for helper modules",
        "agents/openai.yaml surface contract",
        "scripts/__pycache__/ directory",
        "CLI invocation syntax and argument flags for check_plan.py",
        "Inline details of each reference protocol (only gate location and loading condition are shown)"
    ],
    "openQuestions": [],
    "agentInstructions": [
        "Keep entity `id` values stable across diagram updates",
        "Match node `id` in DIAGRAM_DATA with `id` in agent-metadata entities",
        "Add new entities only when supported by SKILL.md evidence or explicit user conversation",
        "Ensure feedback-loop edges (exit-gate -> grill, quality-gate -> plan, verify -> explore) remain visible",
        "The walkthrough follows left-to-right flow through the 4 stages",
        "Do not modify template rendering code (HTML, CSS, JS outside DIAGRAM_DATA and #agent-metadata)"
    ]
}


def replace_diagram_data(text, new_data):
    """Replace the entire DIAGRAM_DATA block."""
    pattern = r'const\s+DIAGRAM_DATA\s*='
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Could not find DIAGRAM_DATA")

    start = match.start()
    depth = 0
    in_string = False
    escape = False
    for i in range(match.end(), len(text)):
        if in_string:
            if escape:
                escape = False
            elif text[i] == '\\':
                escape = True
            elif text[i] == '"':
                in_string = False
            continue
        if text[i] == '"':
            in_string = True
        elif text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                # Include trailing semicolon if present
                if end < len(text) and text[end] == ';':
                    end += 1
                return text[:start] + new_data.strip() + text[end:]
    raise ValueError("Could not find end of DIAGRAM_DATA")


def replace_agent_metadata(text, new_data):
    """Replace the agent-metadata script tag."""
    pattern = r'<script\s+type="application/json"\s+id="agent-metadata">'
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Could not find agent-metadata script tag")

    start = match.start()
    close_match = re.search(r'</script>', text[match.end():])
    if not close_match:
        raise ValueError("Could not find closing script tag")
    end = match.end() + close_match.end()

    new_block = (
        '<script type="application/json" id="agent-metadata">\n'
        + json.dumps(new_data, indent=2, ensure_ascii=False) + '\n'
        '</script>'
    )
    return text[:start] + new_block + text[end:]


def main():
    template_text = TEMPLATE.read_text(encoding="utf-8")

    text = replace_diagram_data(template_text, diagram_data)
    text = replace_agent_metadata(text, agent_metadata)

    # Verify the output has the expected structure
    if 'const DIAGRAM_DATA' not in text:
        raise ValueError("Output missing DIAGRAM_DATA")
    if 'id="agent-metadata"' not in text:
        raise ValueError("Output missing agent-metadata")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Written: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
