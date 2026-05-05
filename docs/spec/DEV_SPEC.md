# DEV_SPEC（中文技术说明）

## 1. 文档目的
本文件面向开发和维护人员，说明模块边界、数据流、调度逻辑、LangGraph ReAct 执行机制以及通知与测试策略。

## 2. 模块分层
- `src/hz_bank_aiops/api/`：HTTP API 与操作入口
- `src/hz_bank_aiops/storage/`：任务表/结果表/审批表存储（SQLite + PostgreSQL）
- `src/hz_bank_aiops/service/`：去重、审批、流程编排
- `src/hz_bank_aiops/agent/`：ReAct 与 LangGraph ReAct
- `src/hz_bank_aiops/tools/`：Zabbix / Doris / 雪狼 / RAG MCP 工具
- `src/hz_bank_aiops/mcp/`：同级 `hz_bank_rag` MCP 客户端
- `src/hz_bank_aiops/notifier/`：飞书通知
- `src/hz_bank_aiops/worker/`：任务抢占和执行

## 3. 入库链路（Flink 阶段）
1. Zabbix 告警和雪狼变更进入 Flink
2. Flink 去重 + 时间窗聚合 + Incident 归并
3. Flink 通过 JDBC 将 Incident 写入 `diagnosis_task`
4. Doris 侧写入历史分析表

对应 SQL：
- `flinksql/01_sources.sql`
- `flinksql/02_incident_aggregation.sql`
- `flinksql/03_task_sink_postgres.sql`
- `flinksql/04_doris_sink.sql`

## 4. 调度与状态
任务状态：
- `NEW`
- `PROCESSING`
- `DONE`
- `FAILED`

调度策略：
- SQLite：按 `priority_rank + created_at` 选取
- PostgreSQL：`FOR UPDATE SKIP LOCKED` 抢占
- 失败重试：`retry_count < max_retry` 回退为 `NEW`

## 5. LangGraph 工作流
工作流位于 `src/hz_bank_aiops/service/workflow.py`。

节点：
1. `dedup`：去重判定
2. `approval`：人工审批判定
3. `react`：执行 LangGraph ReAct（若可用）

分支：
- duplicate -> 直接返回抑制结果
- pending/rejected -> 返回审批结果
- approved/auto_approved -> 进入 ReAct 诊断

## 6. LangGraph ReAct
执行器位于 `src/hz_bank_aiops/agent/langgraph_react.py`。

ReAct 节点：
- `plan`：基于当前 observation 规划下一步 tool call
- `act`：执行 tool，记录 observation
- 循环直至 `final`

Planner：
- `zabbix_realtime_metrics`
- `doris_history_lookup`
- `xuelang_change_lookup`
- `rag_case_search`

## 7. RAG MCP 调用
客户端：`src/hz_bank_aiops/mcp/rag_client.py`

调用协议：
1. `POST /tools/call`
2. 入参固定为 `name + arguments`

默认地址：
- `HZ_AIOPS_RAG_MCP_BASE_URL=http://127.0.0.1:8091`

## 8. 飞书通知
组件：`src/hz_bank_aiops/notifier/feishu.py`

发送时机：
1. 诊断结果落库成功后
2. 再发送飞书 webhook
3. 更新任务 `notify_status`

## 9. demotest（最小化可验证链路）
目录：`demotest/`

特点：
- SQLite 任务表（降格替代 PostgreSQL）
- 伪 Worker + 降格 ReAct 工具
- FastAPI 提供一键 seed、run-once、查看 reasoning
- 可直接验证对 `hz_bank_rag` MCP 的调用

## 10. 测试覆盖
- `tests/test_task_store.py`
- `tests/test_runtime_flow.py`
- `tests/test_control_center.py`
- `tests/test_mcp_client.py`
- `tests/test_worker_runner.py`

## 11. LangGraph ReAct CoT（多步推理轨迹）
本项目在 `LangGraph ReAct` 阶段新增了可选 CoT 轨迹能力，目标是增强诊断可审计性，而不是输出无限制的长推理文本。

配置项：
- `HZ_AIOPS_REACT_COT_ENABLED`：是否开启 CoT 轨迹（默认 `false`）
- `HZ_AIOPS_REACT_COT_MAX_CHARS`：每条轨迹最大字符数（默认 `240`）
- `HZ_AIOPS_REACT_COT_MAX_ENTRIES`：轨迹最大条数（默认 `16`）

实现路径：
- `src/hz_bank_aiops/config.py`：配置定义
- `src/hz_bank_aiops/service/runtime.py`：配置注入工作流
- `src/hz_bank_aiops/service/workflow.py`：注入 LangGraph ReAct 执行器
- `src/hz_bank_aiops/agent/langgraph_react.py`：`plan/act/conclude` 轨迹生成与压缩

输出位置：
- `DiagnosisResult.result_json["cot"]`

示例：
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

说明：若使用 `classic` 工作流或未安装 `langgraph` 且已回退 classic，则不会产出 `cot` 字段。

## 12. LangGraph Sliding Context + Dynamic Summary Memory（新增）
新增配置：
- `HZ_AIOPS_REACT_MEMORY_ENABLED`：是否开启动态记忆（默认 `true`）
- `HZ_AIOPS_REACT_CONTEXT_WINDOW_STEPS`：planner 可见最近步骤数（默认 `3`）
- `HZ_AIOPS_REACT_SUMMARY_MAX_CHARS`：记忆摘要最大字符数（默认 `480`）
- `HZ_AIOPS_REACT_SUMMARY_MAX_ENTRIES`：记忆摘要最大条目数（默认 `12`）

实现要点：
- LangGraph ReAct 维护三层状态：
  - `steps`：滑动窗口上下文（只给 planner 使用）
  - `all_steps`：完整工具轨迹（用于最终 `tool_trace`）
  - `memory_summary`：窗口外历史步骤的动态摘要
- 每次 `act` 后若窗口超限，会把溢出步骤压缩进 `memory_summary`
- planner 同时读取 `completed_actions`（来自 `all_steps`），避免窗口裁剪后重复调用已完成 tool
- 输出新增 `DiagnosisResult.result_json["context_memory"]`

对应实现：
- `src/hz_bank_aiops/agent/langgraph_react.py`
- `src/hz_bank_aiops/config.py`
- `src/hz_bank_aiops/service/runtime.py`
- `src/hz_bank_aiops/service/workflow.py`

测试覆盖：
- `tests/test_langgraph_react_memory.py`

## 13. 当前编排 vs 可优化编排（对照表）

| 维度 | 当前编排（已实现） | 可优化编排（建议） | 预期收益 | 落地点 |
|---|---|---|---|---|
| 主流程骨架 | `dedup -> approval -> react`，LangGraph/Classic 双引擎 | 保持骨架，增加“审批后自动续跑”子流程 | 减少人工二次触发 | `src/hz_bank_aiops/service/workflow.py` |
| 任务状态机 | `NEW -> PROCESSING -> DONE/FAILED` | 增加 `WAIT_APPROVAL`（或 `PENDING_APPROVAL`）显式状态 | 待审批任务语义更清晰 | `src/hz_bank_aiops/storage/task_store.py` |
| 审批流 | pending 时返回“等待审批”结果，需外部再触发 | 审批通过后自动重新入队 | 消除人工补触发 | `src/hz_bank_aiops/service/control_center.py` |
| 去重实现 | 进程内内存索引，重启丢失窗口 | 去重签名落库（Redis/DB）+ TTL | 重启后一致性更好 | `src/hz_bank_aiops/service/control_center.py` |
| Flink->Worker 契约 | `payload_json` 与 `IncidentPayload` 存在字段缺口风险 | 统一 schema 并加契约测试 | 降低 `model_validate` 失败率 | `flinksql/03_task_sink_postgres.sql`、`src/hz_bank_aiops/models/schemas.py` |
| ReAct 计划策略 | 固定工具序列（4 tools） | 条件化路由（先轻探测，再按信号选工具） | 降低平均时延/成本 | `src/hz_bank_aiops/agent/react_agent.py` |
| 上下文控制 | `max_steps=6` + `tool_trace` | 增加证据预算（每步 token/超时预算） | 抑制长尾任务 | `src/hz_bank_aiops/service/runtime.py` |
| CoT | 可选 `cot.trace`，有长度/条数截断 | 分级 CoT（prod 简版/dev 详版）+ 脱敏规则 | 兼顾审计与安全 | `src/hz_bank_aiops/agent/langgraph_react.py`、`src/hz_bank_aiops/config.py` |
| RAG 调用 | 单次 HTTP MCP 调用，失败即记录错误 | 超时分级回退（query -> list_docs -> skip）+ 熔断 | 提高稳定性 | `src/hz_bank_aiops/mcp/rag_client.py` |
| 故障重试 | 任务级重试（`retry_count < max_retry`） | 工具级重试（幂等工具）+ 指数退避 | 降低整任务失败 | `src/hz_bank_aiops/storage/task_store.py`、`src/hz_bank_aiops/tools/ops_tools.py` |
| 可观测性 | 业务级追踪（task/result/tool_trace） | 增加统一 `trace_id` + 指标（p95、成功率、工具错误率） | 更快定位瓶颈 | `src/hz_bank_aiops/service/runtime.py`、`src/hz_bank_aiops/api/main.py` |
| 通知策略 | 结果后飞书通知，失败标记 `FAILED` | 通知重试队列 + 去重通知键 | 降低漏通知/重复通知 | `src/hz_bank_aiops/notifier/feishu.py` |
