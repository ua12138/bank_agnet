from __future__ import annotations
import argparse
from pathlib import Path

STRICT_GUIDE = """# PROJECT_READING_GUIDE

## 1. 一句话结论
这不是“Flink 写任务，Worker 执行，Agent 诊断”就结束的项目。
你真正要学会的是：一条 incident 从 Flink 变成 diagnosis_task，再被 Worker 抢占、被 runtime 编排、被 workflow 分支、被 agent 取证、最后落库与通知的完整闭环。

## 2. 主链路总图
```text
Flink 聚合告警
-> Flink Sink 写 diagnosis_task(status=NEW, payload_json=...)
-> Worker run_once/run_forever
-> task_store.claim_next_task(NEW -> PROCESSING)
-> runtime.process_one_task()
-> IncidentPayload.model_validate(payload_json)
-> workflow.execute()
   -> dedup
   -> approval
   -> diagnose/react
-> task_store.save_result(...)
-> notifier.send(...)
-> task_store.mark_done(...) / mark_failed(...)
```

## 3. 分阶段精读

### Phase 1：Flink 把原始告警变成 incident
**先看文件**
- `flinksql/02_incident_aggregation.sql`

**这一步在做什么**
- 原始告警不是直接给 Agent。
- 先在 Flink 里按窗口、system、service 做聚合，形成一个更适合诊断的 incident。

**样例输入（原始告警，示意）**
```json
[
  {"system": "payment-system", "service": "payment-api", "host": "api-prod-01", "metric": "api.timeout.rate", "severity": "high"},
  {"system": "payment-system", "service": "payment-api", "host": "db-prod-01", "metric": "mysql.connections", "severity": "high"}
]
```

**样例输出（incident_windowed，示意）**
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

**看完这一步后，下一步去看**
- `flinksql/03_task_sink_postgres.sql`

### Phase 2：Flink 把 incident 写成 diagnosis_task
**先看文件**
- `flinksql/03_task_sink_postgres.sql`

**这一步在做什么**
- 把聚合后的 incident 从“流式结果”落成“任务表记录”。
- 从这一刻开始，后续系统围绕 diagnosis_task 这张表处理。

**样例落库记录（示意）**
```json
{
  "task_id": 12,
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "priority": "P1",
  "status": "NEW",
  "retry_count": 0,
  "max_retry": 3,
  "need_notify": true,
  "notify_status": "PENDING",
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

### Phase 3：Worker 抢占任务（NEW -> PROCESSING）
**先看文件**
- `src/hz_bank_aiops/worker/runner.py`
- `src/hz_bank_aiops/storage/task_store.py`

**样例：抢占前后**
```json
{
  "before": {"task_id": 12, "status": "NEW"},
  "after": {"task_id": 12, "status": "PROCESSING", "worker_id": "diag-worker-1"}
}
```

### Phase 4：runtime.process_one_task 编排一次完整处理
**先看文件**
- `src/hz_bank_aiops/service/runtime.py`

**样例输入（字段级 payload_json）**
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

**validate 后对象（示意）**
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

### Phase 5：workflow.execute 决定走 approval 还是 diagnose
**先看文件**
- `src/hz_bank_aiops/service/workflow.py`
- `src/hz_bank_aiops/service/control_center.py`

**样例 state（示意）**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "approval_status": "auto_approved",
  "dedup_hit": false,
  "tool_trace": [],
  "root_cause_top1": ""
}
```

### Phase 6：Agent 先拿证据，再收敛结论
**先看文件**
- `src/hz_bank_aiops/agent/react_agent.py`
- `src/hz_bank_aiops/agent/langgraph_react.py`
- `src/hz_bank_aiops/tools/ops_tools.py`

**样例 tool_trace（示意）**
```json
[
  {"action": "metrics_lookup", "observation": {"cpu": 92, "mysql_conn": 188}},
  {"action": "change_lookup", "observation": {"recent_release": "payment-api-v2.3.1"}},
  {"action": "rag_case_search", "observation": {"matched_case": "connection_pool_exhaustion"}}
]
```

**样例最终结果（示意）**
```json
{
  "root_cause_top1": "DB slow SQL and recent release change jointly caused connection pool exhaustion",
  "confidence": 0.84
}
```

### Phase 7：结果落库、通知、任务终态
**先看文件**
- `src/hz_bank_aiops/storage/task_store.py`
- `src/hz_bank_aiops/notifier/feishu.py`

**样例落库结果（示意）**
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "root_cause_top1": "DB slow SQL and recent release change jointly caused connection pool exhaustion",
  "notify_status": "SENT",
  "task_status": "DONE"
}
```

## 4. 关键知识点精讲

### 任务状态机
- 出现场景：`task_store.py` / `runner.py` / `runtime.py`
- 作用：控制 diagnosis_task 从 `NEW -> PROCESSING -> DONE/FAILED`
- 最低可用理解：任务生命周期的交通灯

### IncidentPayload 强校验
- 出现场景：`runtime.py` / schema/model 文件
- 作用：防止 Flink 写入不完整 payload_json
- 最低可用理解：进入 workflow 前的安检口

### LangGraph state / conditional edge
- 出现场景：`workflow.py`
- 作用：决定 incident 进入 approval 还是 diagnose
- 最低可用理解：带状态的流程图

### ReAct tool_trace
- 出现场景：`react_agent.py` / `langgraph_react.py`
- 作用：记录证据链
- 最低可用理解：不是日志，而是证据链

## 5. 最小调试闭环
1. 手工插入一条 `NEW` 任务
2. 跑一次 Worker 单次执行
3. 看 task 是否变成 `PROCESSING`
4. 看 runtime 是否完成 validate + workflow.execute
5. 看结果是否 save_result
6. 看 notify_status 是否更新
7. 看 task 是否变成 `DONE`

## 6. project_demo.py 对照说明
- `DiagnosisTask` -> diagnosis_task 表记录
- `validate_payload()` -> `IncidentPayload.model_validate(...)`
- `WorkflowState` -> workflow state
- `dedup_node / approval_node / diagnose_node` -> workflow 分支
- `tool_trace` -> agent 证据链
- `save_result / notify / mark_done` -> runtime 收尾
"""
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    Path(args.out).write_text(STRICT_GUIDE, encoding="utf-8")
if __name__ == "__main__":
    main()