# Decision-quality A/B evaluation

`run_decision_quality_ab.py` uses the repository's provider-neutral JSON adapter
protocol. The adapter reads one JSON request from stdin and returns
`{"plan_markdown":"..."}` on stdout. It must honor `model_label`, `load_skill`,
and `skill_root`; the control condition receives `load_skill: false` and a null
skill root.

Run it with one provider adapter and two distinct model labels:

```bash
python tests/skills/plan-change/evals/run_decision_quality_ab.py \
  --adapter python /absolute/path/to/provider_adapter.py \
  --weaker-model weaker-model-id \
  --stronger-model stronger-model-id \
  --output /tmp/plan-change-decision-quality.json
```

The report keeps schema/grounding validity from `check_plan.py` separate from
held-out decision-quality scores and shows the with-skill minus without-skill
delta for each model. No live score movement is claimed until this command is
run with real model adapters.
