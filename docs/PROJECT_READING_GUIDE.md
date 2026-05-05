# PROJECT_READING_GUIDE

面向对象：代码基础较弱、需要快速看懂本项目主链路的同学。  
目标：读完后能明确 `Flink -> Task -> Worker -> Workflow -> Agent -> Result/Notify` 的执行路径。

## 1. 一句话结论
这个项目是一个“告警后诊断”平台：Flink 先把告警聚合成 Incident 写入任务表，Worker 抢任务后通过 LangGraph/ReAct 做诊断，结果落库并可发飞书通知。

## 2. 建议阅读顺序（新手版）
1. 项目目标和验收范围：`docs/README.md`、`docs/spec.md`、`docs/ACCEPTANCE.md`
2. 入口层：`src/hz_bank_aiops/api/main.py`
3. 运行编排层：`src/hz_bank_aiops/service/runtime.py`
4. 存储与调度层：`src/hz_bank_aiops/storage/task_store.py`
5. 工作流决策层：`src/hz_bank_aiops/service/workflow.py`
6. Agent 推理层：`src/hz_bank_aiops/agent/react_agent.py`、`src/hz_bank_aiops/agent/langgraph_react.py`
7. Flink 入库链路：`flinksql/02_incident_aggregation.sql`、`flinksql/03_task_sink_postgres.sql`

## 3. 主链路步骤（含知识点与样例数据）

### Step 1: Flink 聚合告警，形成 Incident
文件：
- `flinksql/02_incident_aggregation.sql`

你需要先懂的知识点：
- `TUMBLE` 时间窗聚合
- `GROUP BY system, service, window_start, window_end`
- 事件合并后生成 `incident_id`

样例（简化后的 incident_windowed 行）：
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "system": "payment-system",
  "service": "payment-api",
  "severity": "high",
  "event_count": 17,
  "window_start": "2025-08-01T10:10:00Z",
  "window_end": "2025-08-01T10:15:00Z",
  "hosts": ["db-prod-01", "api-prod-01", "gw-prod-01"],
  "metrics": ["mysql.connections", "api.timeout.rate", "gateway.5xx.rate"]
}
```

### Step 2: Flink 把 Incident 写入任务表（NEW）
文件：
- `flinksql/03_task_sink_postgres.sql`

你需要先懂的知识点：
- JDBC Sink 到 `diagnosis_task`
- 优先级映射（critical->P0, high->P1）
- 任务初始状态 `NEW`

样例（落库后的任务关键字段）：
```json
{
  "incident_id": "inc_20250801101000_payment-system_payment-api",
  "priority": "P1",
  "status": "NEW",
  "retry_count": 0,
  "max_retry": 3,
  "need_notify": true,
  "notify_status": "PENDING"
}
```

### Step 3: Worker 抢占任务（NEW -> PROCESSING）
文件：
- `src/hz_bank_aiops/worker/runner.py`
- `src/hz_bank_aiops/storage/task_store.py`

你需要先懂的知识点：
- Worker 常驻轮询 `run_forever()` / 单次 `run_once()`
- 抢占语义 `claim_next_task`
- 并发安全：
  - SQLite 按 `priority_rank, created_at` 抢占
  - PostgreSQL 使用 `FOR UPDATE SKIP LOCKED`

样例（Worker 一次处理返回）：
```json
{
  "claimed": true,
  "task_id": 12,
  "incident_id": "inc_20250801_001",
  "status": "DONE"
}
```

### Step 4: Runtime 编排一次任务处理
文件：
- `src/hz_bank_aiops/service/runtime.py`

你需要先懂的知识点：
- 任务生命周期编排：`claim -> validate -> execute -> save -> notify -> mark`
- 入参校验：`IncidentPayload.model_validate(...)`
- 异常处理：`mark_failed(..., retryable=True)`

样例（API 单次触发 Worker）：
```http
POST /api/v1/workers/run-once
```

响应样例（成功）：
```json
{
  "claimed": true,
  "task_id": 1,
  "incident_id": "inc_20250801_001",
  "status": "DONE",
  "notify_status": "SENT"
}
```

### Step 5: Workflow 决策（去重 -> 审批 -> ReAct）
文件：
- `src/hz_bank_aiops/service/workflow.py`
- `src/hz_bank_aiops/service/control_center.py`

你需要先懂的知识点：
- 状态图思维（LangGraph 节点与条件路由）
- 去重签名（system/service/severity/hosts/metric keys）
- 人工审批状态（pending/approved/rejected/auto_approved）

样例（待审批时的诊断结果）：
```json
{
  "incident_id": "inc_20250801_002",
  "root_cause_top1": "Waiting for human approval",
  "result_json": {
    "workflow_engine": "langgraph",
    "approval_status": "pending"
  }
}
```

### Step 6: Agent ReAct 调用工具并生成根因
文件：
- `src/hz_bank_aiops/agent/react_agent.py`
- `src/hz_bank_aiops/agent/langgraph_react.py`
- `src/hz_bank_aiops/tools/ops_tools.py`

你需要先懂的知识点：
- ReAct 循环：`thought -> tool_call -> observation -> final`
- 工具抽象（metrics/history/change/rag）
- `tool_trace` 证据链

样例（简化 reasoning）：
```json
[
  {"action": "zabbix_realtime_metrics", "observation": {"ok": true}},
  {"action": "doris_history_lookup", "observation": {"ok": true}},
  {"action": "xuelang_change_lookup", "observation": {"ok": true}},
  {"action": "rag_case_search", "observation": {"ok": true}}
]
```

### Step 7: 结果落库与通知
文件：
- `src/hz_bank_aiops/storage/task_store.py`
- `src/hz_bank_aiops/notifier/feishu.py`

你需要先懂的知识点：
- `diagnosis_result` 落库
- `notify_status` 更新
- 任务终态：`DONE` / `FAILED`

样例（结果关键字段）：
```json
{
  "incident_id": "inc_20250801_001",
  "root_cause_top1": "DB slow SQL and recent release change jointly caused connection pool exhaustion",
  "confidence": 0.84,
  "notify_status": "SENT"
}
```

## 4. 关键文件职责速查
- `src/hz_bank_aiops/api/main.py`：对外 API 入口（提交任务、触发 worker、审批）。
- `src/hz_bank_aiops/service/runtime.py`：一次任务处理总编排。
- `src/hz_bank_aiops/storage/task_store.py`：任务表、结果表、审批表和状态流转。
- `src/hz_bank_aiops/service/workflow.py`：去重/审批/诊断的流程决策。
- `src/hz_bank_aiops/agent/*.py`：ReAct 推理执行。
- `flinksql/*.sql`：流式阶段的数据聚合与任务入库。

## 5. 新手最低可用调试路径
1. 先用样例入队：`python scripts/seed_incidents.py`
2. 单次消费任务：`python scripts/run_worker_once.py`
3. 看任务状态：`GET /api/v1/tasks`
4. 看审批记录（若 pending）：`GET /api/v1/approvals/{incident_id}`
5. 再跑一次 worker 验证闭环

## 6. 当前实现的一个注意点
`IncidentPayload` 是严格模型。  
如果 Flink 写入的 `payload_json` 字段不完整（例如缺失 `hosts/metrics` 结构），Worker 在 `model_validate` 会失败并进入重试/失败分支。  
因此生产化时需要确保 Flink Sink 的 payload 与 `src/hz_bank_aiops/models/schemas.py` 中 `IncidentPayload` 一致。
