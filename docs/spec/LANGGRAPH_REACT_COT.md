# LangGraph ReAct CoT Design

## Goal
Add optional multi-step reasoning trace (CoT) to the LangGraph ReAct loop while keeping classic ReAct unchanged.

This project uses **structured CoT trace**, not free-form hidden reasoning dumps:
- `plan`: why the next tool is selected
- `observe`: compact summary of tool observation
- `conclude`: final convergence signal

## Why this design
- Improves diagnosis auditability for ops engineers.
- Keeps token and storage growth under control with hard limits.
- Avoids coupling to any single model provider.

## Config
CoT related configs:

- `HZ_AIOPS_REACT_COT_ENABLED` (bool, default `false`)
- `HZ_AIOPS_REACT_COT_MAX_CHARS` (int, default `240`)
- `HZ_AIOPS_REACT_COT_MAX_ENTRIES` (int, default `16`)

Context memory related configs (new):
- `HZ_AIOPS_REACT_MEMORY_ENABLED` (bool, default `true`)
- `HZ_AIOPS_REACT_CONTEXT_WINDOW_STEPS` (int, default `3`)
- `HZ_AIOPS_REACT_SUMMARY_MAX_CHARS` (int, default `480`)
- `HZ_AIOPS_REACT_SUMMARY_MAX_ENTRIES` (int, default `12`)

Path: `src/hz_bank_aiops/config.py`

## Execution Path
Config flow:
`Settings -> DiagnosisRuntime -> IncidentDiagnosisWorkflow -> LangGraphReActExecutor`

When `workflow_engine=langgraph` and CoT is enabled:
1. `plan` node appends one compact planning line.
2. `act` node appends one compact observation line.
3. `final` appends one conclusion line.

Result payload adds:

```json
{
  "cot": {
    "enabled": true,
    "trace": [
      "Step 1 - plan: ... -> call zabbix_realtime_metrics",
      "Step 1 - observe(zabbix_realtime_metrics): ...",
      "Step 2 - plan: ... -> call doris_history_lookup"
    ]
  }
}
```

Path: `src/hz_bank_aiops/agent/langgraph_react.py`

## Sliding Context + Dynamic Summary Memory (new)
The LangGraph ReAct executor now has two additional state layers:

- `steps`: sliding window steps for planner context (recent N only)
- `all_steps`: full tool trace for final result
- `memory_summary`: compressed summary from older steps pushed out of the window

When `HZ_AIOPS_REACT_MEMORY_ENABLED=true`:
1. `act` appends the new step into both `all_steps` and `steps`.
2. If `len(steps) > context_window_steps`, overflow steps are summarized into `memory_summary`.
3. Planner receives:
   - recent `steps`
   - `memory_summary`
   - `completed_actions` from `all_steps` (prevents repeated tool calls after window trimming).

Result payload adds:

```json
{
  "context_memory": {
    "enabled": true,
    "window_steps": 3,
    "window_step_count": 3,
    "all_step_count": 4,
    "summary": "Step 1 zabbix_realtime_metrics [ok] ...",
    "summary_snapshots": ["..."]
  }
}
```

## Guardrails
- CoT lines are clipped by `react_cot_max_chars`.
- CoT list is clipped by `react_cot_max_entries`.
- For large list observations, only first item + count is kept.

## Test Coverage
`tests/test_langgraph_react_cot.py`

- `test_langgraph_writes_cot_trace_when_enabled`
- `test_langgraph_does_not_write_cot_trace_when_disabled`

If `langgraph` package is not installed, tests auto-skip.

Additional memory tests:
- `tests/test_langgraph_react_memory.py`
  - summary generated when memory is enabled
  - summary empty when memory is disabled
