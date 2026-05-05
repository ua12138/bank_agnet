# SPEC（总览）

## 1. 项目定位
BANK_AGENT 是一个“告警后诊断”平台：
- 上游（Flink SQL）负责告警聚合、Incident 归并与任务入队。
- 中游（Worker + Workflow）负责任务消费、去重、审批、ReAct 推理。
- 下游负责结果落库与通知发送。

## 2. 主链路（一句话）
`Flink -> diagnosis_task -> Worker -> Workflow(dedup/approval/react) -> diagnosis_result -> notify`

## 3. 核心模块职责
- `src/hz_bank_aiops/api/`：FastAPI 接口层。
- `src/hz_bank_aiops/service/`：运行时装配、治理中台、编排流程。
- `src/hz_bank_aiops/agent/`：ReAct 与 LangGraph ReAct 执行。
- `src/hz_bank_aiops/storage/`：任务/结果/审批存储（SQLite、PostgreSQL）。
- `src/hz_bank_aiops/tools/`：指标、历史、变更、RAG 工具封装。
- `src/hz_bank_aiops/mcp/`：RAG MCP 客户端。
- `src/hz_bank_aiops/notifier/`：飞书通知。
- `src/hz_bank_aiops/worker/`：任务轮询消费。

## 4. Flink 侧交付
- `flinksql/01_sources.sql`
- `flinksql/02_incident_aggregation.sql`
- `flinksql/03_task_sink_postgres.sql`
- `flinksql/04_doris_sink.sql`

样例数据：
- `data/sample/zabbix_alerts.jsonl`
- `data/sample/xuelang_changes.jsonl`
- `data/sample/incidents.json`

## 5. 关键策略
- 去重（dedup）：按事件特征生成签名，在窗口期内判重。
- 审批（approval）：支持 `pending/approved/rejected/auto_approved`。
- 重试（retry）：失败任务在 `retry_count < max_retry` 时回到 `NEW`。
- 通知（notify）：结果落库后发送飞书，发送状态写回任务表。

## 6. 相关文档
- 开发规格：`docs/spec/DEV_SPEC.md`
- 验收步骤：`docs/ACCEPTANCE.md`
- OpenAPI：`docs/spec/openapi.yaml`
- 新手导读：`PROJECT_READING_GUIDE.md`
- CoT 设计：`docs/spec/LANGGRAPH_REACT_COT.md`
- 上下文记忆设计：`docs/spec/LANGGRAPH_CONTEXT_MEMORY.md`
