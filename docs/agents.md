# Engineering Agents Overview

Agents are focused, role-based orchestration layers built on top of canonical engineering skills.

## Platform Support & Distribution Matrix

| Platform | Skills Distributed | Agents Distributed | Scope |
| --- | ---: | ---: | --- |
| Claude Code plugin | Yes | Yes | Installed plugin |
| Cursor plugin | Yes | Yes | Installed plugin |
| Codex skill installation | Yes | No automatic custom-agent installation | Installed skills |
| Codex repository clone | Yes | Yes | Current project |
| Codex explicit installer | Existing installed skills | Yes | Selected target project |

## Available Agents

| Agent | Status | Repo Write | Web Research | Skills Included | Summary |
| --- | --- | --- | --- | --- | --- |
| [architecture-engineer](./agents/architecture-engineer.md) | `stable` | `False` | `True` | `design-codebase-with-senior-dev`, `create-diagram`, `plan-with-senior-dev` | Analyze and redesign codebase architecture without implementing changes. |
| [delivery-engineer](./agents/delivery-engineer.md) | `stable` | `True` | `True` | `plan-with-senior-dev`, `implement-with-senior-dev` | Turn a concrete engineering request into a validated plan and execute an authorized implementation plan. |
| [issue-resolution-engineer](./agents/issue-resolution-engineer.md) | `stable` | `True` | `True` | `github-issue-planner`, `plan-with-senior-dev`, `implement-with-senior-dev` | Inspect GitHub issues, reconcile issue claims with local checkout, and plan or implement authorized fixes. |
| [codebase-health-engineer](./agents/codebase-health-engineer.md) | `stable` | `False` | `True` | `codebase-issue-auditor`, `design-codebase-with-senior-dev`, `optimize-codebase-with-senior-dev`, `create-diagram` | Audit codebase health, discover risks and test gaps, assess structural pressure, and target measurable optimizations. |
