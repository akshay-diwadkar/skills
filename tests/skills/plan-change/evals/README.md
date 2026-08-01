# Agent-first A/B evaluation

`run_agent_first_ab.py` compares native planning with plan-change v6 using the
same model, effort, fixture, prompt, and environment. The provider adapter reads
one JSON request and returns:

```json
{"plan_markdown":"...","metrics":{"wall_clock_ms":1,"input_tokens":1,"output_tokens":1,"tool_calls":1,"repository_reads":1,"repository_searches":1,"repository_wide_script_searches":0,"script_duration_ms":1,"opened_paths":[],"bytes_read":0,"seal_attempts":1,"evidence_valid":1}}
```

The blinded judge adapter receives the prompt, plan, and ten dimension names
and returns one numeric score per dimension. The report enforces the runtime,
token, search, seal-attempt, evidence-validity, and quality gates declared in
`v6_scenarios.json`.
