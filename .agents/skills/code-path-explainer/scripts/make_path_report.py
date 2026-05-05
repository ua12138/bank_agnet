from __future__ import annotations
import argparse
from pathlib import Path

STRICT_REPORT = """# CODE_PATH_REPORT

## 1. 功能结论
真正要展开的是：这条 incident 怎样被写入 diagnosis_task，再怎样被 Worker 抢占，再怎样被 runtime 跳到 workflow，再怎样进入 agent，最后怎样 save / notify / mark。

## 2. 全局链路图
```mermaid
flowchart TD
  A[Flink incident_windowed]
  B[INSERT diagnosis_task(status=NEW, payload_json)]
  C[runner.run_forever/run_once]
  D[task_store.claim_next_task NEW->PROCESSING]
  E[runtime.process_one_task]
  F[IncidentPayload.model_validate]
  G[workflow.execute]
  H[dedup]
  I[approval]
  J[react diagnose]
  K[save_result]
  L[notify]
  M[mark_done/mark_failed]
  A --> B --> C --> D --> E --> F --> G
  G --> H --> I --> J --> K --> L --> M
```

## 3. 逐步跳转展开

### Step 1：Flink 把 incident 写入 diagnosis_task
**文件**
- `flinksql/03_task_sink_postgres.sql`

**示意输入**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "system": "payment-system",
  "service": "payment-api",
  "severity": "high",
  "hosts": ["api-prod-01", "db-prod-01"],
  "metrics": ["api.timeout.rate", "mysql.connections"]
}
```

**示意输出**
```json
{
  "task_id": 12,
  "status": "NEW",
  "priority": "P1",
  "payload_json": {
    "incident_id": "inc_20250801101000_payment-system_payment-api",
    "system": "payment-system",
    "service": "payment-api",
    "severity": "high",
    "hosts": ["api-prod-01", "db-prod-01"],
    "metrics": ["api.timeout.rate", "mysql.connections"],
    "need_approval": false
  }
}
```

### Step 2：Worker 轮询并跳到 claim_next_task
**文件**
- `src/hz_bank_aiops/worker/runner.py`

**你应该看到的跳转代码形态**
```python
task = task_store.claim_next_task(worker_id=...)
if not task:
    return {"claimed": False}
return runtime.process_one_task(task)
```

**这一跳传过去的数据**
```json
{
  "worker_id": "diag-worker-1",
  "expected_task_status": "NEW"
}
```

**下一跳接收位置**
- `src/hz_bank_aiops/storage/task_store.py`
- `claim_next_task(...)`

### Step 3：claim_next_task 把 NEW 改成 PROCESSING
**文件**
- `src/hz_bank_aiops/storage/task_store.py`

**状态变化**
```json
{
  "before": {"task_id": 12, "status": "NEW"},
  "after": {"task_id": 12, "status": "PROCESSING", "worker_id": "diag-worker-1"}
}
```

**返回给 runtime 的 task（示意）**
```json
{
  "task_id": 12,
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "status": "PROCESSING",
  "payload_json": {
    "incident_id": "inc_20250801101000_payment-system_payment-api",
    "system": "payment-system",
    "service": "payment-api",
    "severity": "high",
    "hosts": ["api-prod-01", "db-prod-01"],
    "metrics": ["api.timeout.rate", "mysql.connections"],
    "need_approval": false
  }
}
```

### Step 4：runtime.process_one_task 先 validate，再跳到 workflow.execute
**文件**
- `src/hz_bank_aiops/service/runtime.py`

**你真正要看的跳转代码形态**
```python
payload = IncidentPayload.model_validate(task.payload_json)
diagnosis_result = workflow.execute(payload)
save_result(...)
notify(...)
mark_done(...)
```

**传入 validate 的字段级样例**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "system": "payment-system",
  "service": "payment-api",
  "severity": "high",
  "hosts": ["api-prod-01", "db-prod-01"],
  "metrics": ["api.timeout.rate", "mysql.connections"],
  "need_approval": false
}
```

**validate 后传给 workflow 的对象（示意）**
```json
{
  "IncidentPayload": {
    "incident_id": "inc_20250801101000_payment-system_payment-api",
    "system": "payment-system",
    "service": "payment-api",
    "severity": "high",
    "hosts": ["api-prod-01", "db-prod-01"],
    "metrics": ["api.timeout.rate", "mysql.connections"],
    "need_approval": false
  }
}
```

### Step 5：workflow.execute 决定走 approval 还是 diagnose
**文件**
- `src/hz_bank_aiops/service/workflow.py`

**样例 state**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "approval_status": "auto_approved",
  "dedup_hit": false,
  "tool_trace": [],
  "root_cause_top1": ""
}
```

**走 approval 分支时**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "approval_status": "pending",
  "root_cause_top1": "Waiting for human approval"
}
```

### Step 6：Agent 通过 tool_trace 取证
**文件**
- `src/hz_bank_aiops/agent/react_agent.py`
- `src/hz_bank_aiops/agent/langgraph_react.py`

**示意 tool_trace**
```json
[
  {"action": "metrics_lookup", "observation": {"cpu": 92, "mysql_conn": 188}},
  {"action": "change_lookup", "observation": {"recent_release": "payment-api-v2.3.1"}},
  {"action": "rag_case_search", "observation": {"matched_case": "connection_pool_exhaustion"}}
]
```

**示意输出**
```json
{
  "root_cause_top1": "DB slow SQL and recent release change jointly caused connection pool exhaustion",
  "confidence": 0.84
}
```

### Step 7：runtime 收尾：save_result / notify / mark_done
**文件**
- `src/hz_bank_aiops/service/runtime.py`
- `src/hz_bank_aiops/storage/task_store.py`
- `src/hz_bank_aiops/notifier/feishu.py`

**示意最终结果**
```json
{
  "task_id": 12,
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "task_status": "DONE",
  "notify_status": "SENT",
  "root_cause_top1": "DB slow SQL and recent release change jointly caused connection pool exhaustion"
}
```

## 4. 关键状态对象表
- `diagnosis_task`: `task_id`, `status`, `payload_json`, `notify_status`
- `IncidentPayload`: incident 核心字段
- `WorkflowState`: `approval_status`, `dedup_hit`, `tool_trace`, `root_cause_top1`
- `DiagnosisResult`: `root_cause_top1`, `confidence`, `tool_trace`

## 5. 新人必须先懂的机制
1. 任务表解耦
2. claim 语义
3. runtime 是总编排
4. workflow 是网关
5. tool_trace 是证据链
"""
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    Path(args.out).write_text(STRICT_REPORT, encoding="utf-8")
if __name__ == "__main__":
    main()