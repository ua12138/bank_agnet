# Final Project Review

## 1. Project Background
这是一个银行运维场景下的事件诊断服务。它不直接处理原始告警流，而是假设上游 Flink 已经把多条告警归并成 `incident`，Python 服务负责后续诊断与处理。

## 2. Architecture Summary
整体架构可以分成五层：
- API 层：收 incident，暴露查询与审批接口
- Runtime 层：装配各类依赖
- Workflow 层：去重、审批、进入 Agent
- Agent 层：按 ReAct 方式调用工具并收敛结果
- Storage / Notification / MCP 层：负责落库、通知和外部知识调用

## 3. Main Flow Explanation
最关键的闭环是：
1. `POST /api/v1/incidents` 创建任务
2. Worker 认领任务
3. Workflow 判断是否重复、是否需要审批
4. Agent 收集 observation 并生成诊断
5. 结果落库
6. 发送通知

## 4. Core Technical Decisions
- 用任务表把 API 与诊断执行解耦
- 用 `DiagnosisRuntime` 统一装配依赖
- 用 `IncidentControlCenter` 承载治理逻辑
- 用 `classic` + `langgraph` 双实现支持降级
- 用 MCP 调外部 RAG，而不是把全部知识库逻辑塞进本仓库

## 5. Difficult Points
- 你需要同时理解“治理逻辑”和“推理逻辑”
- 任务状态机和审批状态是两套概念
- LangGraph 版 ReAct 还引入了 `steps`、`all_steps`、`context_memory`
- `planner_mode` 可能在真实 LLM 与 mock planner 之间自动切换

## 6. Engineering Tradeoffs
- 优点：
  - 模块边界清晰
  - 本地可用 SQLite 学习
  - 具备 fallback 逻辑
- 代价：
  - 需要同时理解 API、Worker、存储、工作流、Agent
  - 外部 RAG 不在本仓库内，学习时需要“隔一层”理解

## 7. Interview-Ready Version
“这是一个 AIOps 事件诊断后端。系统接收上游归并后的 incident，将其写入任务表，再由 Worker 异步消费。消费过程中先做去重和审批，再进入 ReAct 诊断流程。Agent 会依次调用指标、历史、变更和外部 RAG MCP 工具，汇总证据后输出根因、建议和工具轨迹。系统支持 SQLite 本地学习路径和 PostgreSQL 生产路径，并且提供 classic 与 LangGraph 两种 workflow 执行方式。”

## 8. Risks in Overclaiming
- 不要说“仓库内实现了完整 RAG 系统”，因为这里只看到 `RagMCPClient` 调外部服务。
- 不要说“项目使用 LangChain”，因为仓库依赖和代码里都没有验证到。
- 不要说“已经实现分布式调度系统”，因为这里只看到基于任务表和 Worker 的基础消费模式。
- 不要说“LLM 一定参与每次诊断”，因为没有 `LLM API KEY` 时会降级到 mock planner。
- 不要说“所有工具都是真实外部系统”，因为 `ops_tools.py` 里大量是 mock data。

## 9. What I Still Need to Learn
- FastAPI 路由与请求体验证
- SQLite / PostgreSQL 任务状态机
- ReAct 的 observation 驱动思路
- LangGraph 的状态更新与条件边
- MCP 调用模式
- 如何从测试反推主流程
