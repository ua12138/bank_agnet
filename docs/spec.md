# SPEC.md

## 1. 项目名称
基于 Flink + Doris + LLM Agent 的智能运维事件诊断平台

## 2. 目标
本项目聚焦“告警后诊断”：
- Flink 负责告警去重、时间窗聚合、Incident 归并
- Worker 负责从任务表抢占任务并执行 LangGraph ReAct 诊断
- Agent 负责多工具证据收集与根因推理
- 结果落库并通过飞书 Webhook 通知
- 可调用同级 `hz_bank_rag` 项目的 MCP 服务作为 RAG 工具

## 3. 架构
```text
Zabbix/XueLang -> FlinkSQL -> PostgreSQL diagnosis_task
                                  -> Worker -> LangGraph Workflow
                                               -> Dedup Gate
                                               -> Approval Gate
                                               -> LangGraph ReAct (tool loop)
                                               -> Diagnosis Result
                                  -> PostgreSQL diagnosis_result
                                  -> Feishu Webhook
                                  -> Doris (离线沉淀，FlinkSQL 示例提供)
```

## 4. 核心模块
- `src/hz_bank_aiops/storage/`：任务表与结果表存储（SQLite + PostgreSQL）
- `src/hz_bank_aiops/worker/`：任务抢占、失败重试、通知状态更新
- `src/hz_bank_aiops/agent/`：ReAct 与 LangGraph ReAct
- `src/hz_bank_aiops/service/`：去重、人工审批、流程编排
- `src/hz_bank_aiops/notifier/`：飞书 webhook
- `src/hz_bank_aiops/mcp/`：RAG MCP 客户端
- `src/hz_bank_aiops/api/`：FastAPI 服务

## 5. Flink 阶段交付
- `flinksql/01_sources.sql`：Zabbix / 雪狼 source 定义
- `flinksql/02_incident_aggregation.sql`：事件窗口聚合与 Incident 归并
- `flinksql/03_task_sink_postgres.sql`：写入 `diagnosis_task`
- `flinksql/04_doris_sink.sql`：写入 Doris 事实表
- `data/sample/*.jsonl|json`：样例输入与 Incident 数据

## 6. 人工审批与去重策略
- 去重签名：`system + service + severity + hosts + metric keys`
- 去重窗口：`HZ_AIOPS_DEDUP_WINDOW_SEC`
- 审批规则：
  - `HZ_AIOPS_ENABLE_HUMAN_APPROVAL=false`：自动放行
  - `critical/high` 默认进入审批；低中风险自动放行
  - 审批接口：`/api/v1/approvals/{incident_id}`

## 7. Worker 调度策略
- 任务状态：`NEW -> PROCESSING -> DONE/FAILED`
- 失败重试：`retry_count < max_retry` 时回到 `NEW`
- 抢任务：
  - SQLite：按 `priority_rank, created_at` 抢占
  - PostgreSQL：使用 `FOR UPDATE SKIP LOCKED`（代码已实现）

## 8. RAG MCP 调用
- 客户端：`src/hz_bank_aiops/mcp/rag_client.py`
- 默认地址：`HZ_AIOPS_RAG_MCP_BASE_URL=http://127.0.0.1:8091`
- 工具链中 `rag_case_search` 统一调用 `/tools/call`（`name + arguments`）

## 9. 飞书通知
- 组件：`src/hz_bank_aiops/notifier/feishu.py`
- 在结果落库后执行，失败不会回滚诊断结果
- 任务表 `notify_status` 记录发送状态

## 10. demotest 最小化通路
- 目录：`demotest/`
- 技术：FastAPI + SQLite task/result + 伪 ReAct Worker
- 能力：
  - 伪输入 Incident 入队
  - Worker 执行降格 Tool（metrics/change/rag）
  - 输出完整 reasoning 过程
  - 可验证对 `hz_bank_rag` MCP 的调用

## 11. 验收产物
- 开发说明：`docs/spec/DEV_SPEC.md`
- 快速上手：`docs/README.md`
- 验收步骤：`docs/ACCEPTANCE.md`
- API 定义：`docs/spec/openapi.yaml`
- demotest 调试手册：`docs/demotest/RUNBOOK.md`
- LangGraph ReAct CoT 设计：`docs/spec/LANGGRAPH_REACT_COT.md`
- LangGraph Sliding Context + Dynamic Memory：`docs/spec/LANGGRAPH_CONTEXT_MEMORY.md`

## 12. LangGraph ReAct CoT（新增）
- 新增可选 CoT 轨迹开关：`HZ_AIOPS_REACT_COT_ENABLED`
- 限制每条轨迹长度：`HZ_AIOPS_REACT_COT_MAX_CHARS`
- 限制轨迹条数：`HZ_AIOPS_REACT_COT_MAX_ENTRIES`
- 仅在 `workflow_engine=langgraph` 时生效
- 诊断输出新增 `result_json.cot.trace`（plan/observe/conclude）

## 13. LangGraph Sliding Context + Dynamic Summary Memory（新增）
- 新增记忆开关：`HZ_AIOPS_REACT_MEMORY_ENABLED`
- 滑动窗口：`HZ_AIOPS_REACT_CONTEXT_WINDOW_STEPS`
- 摘要长度与条数：
  - `HZ_AIOPS_REACT_SUMMARY_MAX_CHARS`
  - `HZ_AIOPS_REACT_SUMMARY_MAX_ENTRIES`
- LangGraph ReAct 同时维护：
  - `steps`：最近 N 步（供 planner 推理）
  - `all_steps`：完整工具轨迹（供审计与输出）
  - `memory_summary`：窗口外历史步骤的动态摘要
- 诊断输出新增：`result_json.context_memory`

## 14. 设计问答

### Q1. LangGraph 相比传统 ReAct while 循环有什么优势？
- LangGraph 的核心优势是状态显式化、节点显式化、路由显式化。
- 传统 `while` 循环适合单一线性的 `plan -> act -> observe` 回路；一旦加入去重、审批、重试、人工接管、回退分支，代码会迅速变成大量 if/else。
- 本项目把 `dedup -> approval -> react` 建模为图节点，因此治理逻辑和诊断逻辑能够清晰分层。

### Q2. 如果 Agent 执行到第 5 步才发现第 2 步工具结果错了，LangGraph 如何支持回溯或重新执行？
- 当前实现还没有提供真正的 step 级回溯与重放能力。
- 现阶段的做法是把错误 observation 保留在 `tool_trace` 中，让后续步骤基于新证据继续修正。
- 如果确实需要完整重跑，当前 fallback 是任务重试或人工重新触发。
- LangGraph 天然适合补 `checkpoint + reroute + replay`，但这属于下一阶段增强，不是当前版本已经实现的能力。

### Q3. Observation 和预期不符时，Agent 如何调整后续步骤？
- tool 失败不会立刻中断整条链路。
- tool 结果会记录为 `observation = {"ok": false, "error": ...}`，并保留在推理轨迹中。
- 后续 planner 会结合当前 observation、滑动窗口上下文和动态摘要记忆继续决定下一步。

### Q4. MCP 工具列表是静态注册还是动态发现？
- 当前项目使用的是静态注册。
- `build_default_tools()` 固定装配以下工具：
- `zabbix_realtime_metrics`
- `doris_history_lookup`
- `xuelang_change_lookup`
- `rag_case_search`
- 其中只有 `rag_case_search` 会在内部调用外部 MCP 服务。
- 当前代码没有实现“启动时从 MCP server 拉取工具列表并动态挂载”。

### Q5. 为什么这个场景用 Agent，而不是普通 Workflow？
- 普通 Workflow 更适合固定路径、固定顺序的处理流程。
- AIOps 诊断不是固定路径：有时先看实时指标，有时更需要变更记录或历史案例，下一步依赖上一轮 observation。
- 所以本项目采用的是组合式设计：
- 外层 Workflow 负责确定性的治理
- 内层 Agent 负责动态诊断

### Q6. Agent 每一步推理和行动有没有日志记录？
- 有，但主要是结构化轨迹留痕，而不是完整统一的 logger 体系。
- 每一步记录在 `tool_trace` 中，包含：
- `index`
- `thought`
- `action`
- `action_input`
- `observation`
- 任务层还会记录：
- `status`
- `retry_count`
- `worker_id`
- `started_at`
- `finished_at`
- `error_message`
- `notify_status`

### Q7. Agent 怎么监控？关键指标有哪些？
- 当前代码已经暴露了足够的原始数据做监控，但还没有自带完整 dashboard。
- 建议重点监控：
- 任务吞吐量
- 成功率 / 失败率
- 平均时延与 P95 时延
- 单任务平均 tool 步数
- 各 tool 成功率 / 错误率
- MCP 可用性与超时率
- 飞书通知成功率
- 审批 pending 数量
- 重试率

### Q8. Agent 能力怎么评估？
- 评估建议分三层：
- 离线准确性：Top1 根因准确率、Top3 recall
- 流程质量：平均步数、无效 tool 比例、RAG 命中率、人工接管率
- 业务收益：冗余告警下降、误报下降、MTTD / MTTR 改善、排查时间下降
- 对这个项目来说，最合理的评估对象是“传统规则流 vs Agent 流”，而不是只看模型生成文本是否看起来合理。

### Q9. 为什么这个项目用的是 LangGraph 而不是 LangChain？
- LangChain 更偏组件化、链式封装。
- LangGraph 更适合有状态、多节点、多分支、可恢复的执行图。
- 本项目的核心难点不是单次 prompt 调用，而是诊断任务如何在治理节点和推理步骤之间流转，因此 LangGraph 更贴合。

### Q10. 框架是否自带幻觉处理？
- 不自带完整闭环的幻觉治理能力。
- LangGraph 提供的是编排能力，不是事实校验能力。
- 本项目当前的抗幻觉手段主要来自：
- 多工具 observation
- RAG 外部证据
- 可审计的 `tool_trace`
- 人工审批与人工接管
- 自动事实校验、交叉裁决、自反思循环等机制，目前还没有内建。

### Q11. Skills 是否能替代部分工具？
- Skills 可以替代一部分“软能力”，但不能替代数据访问型工具。
- Skills 更适合提供分析套路、总结模板、知识组织方式。
- 它不能替代实时指标查询、历史案例检索、变更平台查询、以及基于 MCP 的 RAG 检索，因为这些都依赖真实外部数据。

### Q12. A/B 测试分流策略
- 分流应按 `incident_id` 或 `service/system` 做稳定路由，而不是按单次请求随机分配。
- 推荐策略：
- 对照组：传统规则流
- 实验组：Agent 诊断流
- 分流键：`hash(incident_id) % 100`，保证同一 incident 全链路只进入同一个实验桶
- 核心观测维度：
- 根因准确率
- 冗余告警过滤率
- 平均排查时长
- 人工介入率
- 通知成功率
- 任务失败 / 回退率
- 实验期间必须锁定模型版本、Prompt 版本、Tool 集合版本，否则实验结果不可比。
