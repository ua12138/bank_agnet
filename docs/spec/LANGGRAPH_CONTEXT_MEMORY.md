# LangGraph Context Memory Design

## 1. Problem
Pure ReAct loops keep appending tool observations into context.  
As steps grow, prompt size grows, latency rises, and attention quality can drop.

## 2. Goal
Implement a real context management mechanism for LangGraph ReAct:
- Sliding context window for recent steps.
- Dynamic summary memory for older steps.
- Keep full tool trace for auditability.

## 3. State Model
In `src/hz_bank_aiops/agent/langgraph_react.py`:

- `steps`: recent steps for planner context only.
- `all_steps`: complete tool trace for final output.
- `memory_summary`: compressed summary of old overflow steps.
- `memory_snapshots`: rolling snapshots for observability.

## 4. Execution Rules
1. `plan` uses:
   - `steps` (recent window)
   - `memory_summary`
   - `completed_actions` extracted from `all_steps`
2. `act` appends a new tool step.
3. If `len(steps) > window`, old steps are summarized into `memory_summary`.
4. Final diagnosis still uses `all_steps`.

## 5. Why `completed_actions` is required
If planner only sees the sliding window, old tool calls can disappear from visible context, causing repeated calls.  
`completed_actions` avoids this by preserving global completion knowledge.

## 6. Config
- `HZ_AIOPS_REACT_MEMORY_ENABLED=true|false`
- `HZ_AIOPS_REACT_CONTEXT_WINDOW_STEPS=3`
- `HZ_AIOPS_REACT_SUMMARY_MAX_CHARS=480`
- `HZ_AIOPS_REACT_SUMMARY_MAX_ENTRIES=12`

## 7. Output Contract
`DiagnosisResult.result_json.context_memory`:

```json
{
  "enabled": true,
  "window_steps": 3,
  "window_step_count": 3,
  "all_step_count": 4,
  "summary": "Step 1 zabbix_realtime_metrics [ok] ...",
  "summary_snapshots": ["..."]
}
```

## 8. Validation
`tests/test_langgraph_react_memory.py` covers:
- memory enabled: summary is generated, window count is capped
- memory disabled: summary is empty
